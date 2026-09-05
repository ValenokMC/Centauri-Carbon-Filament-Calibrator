# -*- coding: utf-8 -*-
"""The calibration dialog: material, spool, then the plate menu.

Plates can be entered in any order and across several sittings - answers are
kept in the spool's folder and offered back on the next run. A calibration
takes hours with a print between plates, and keeping a session open through
that is not a reasonable thing to ask.

The preset is rebuilt after every accepted measurement, so the next plate
prints on the values found so far. That is also why the plates have an order:
flow is measured at the final temperature, PA at the final flow, max flow at
the final PA.
"""
import json
import os
import uuid

from . import config as config_mod
from . import console as c
from . import formulas, journal, names, orca, paths, presets, scales
from . import templates as templates_mod
from . import support
from . import run_context


class Session(object):

    def __init__(self, cfg, scales_data, dry_run=False):
        self.cfg = cfg
        self.scales = scales_data
        self.dry_run = dry_run
        self.material = None
        self.spool = None
        self.base = None
        self.tests = []
        self.measurements = {}
        self.folder = None
        self.base_values = {}
        self.profiles = {}
        self.context = run_context.from_config(cfg)
        self.run_id = None
        self.context_changed_from = 0
        # Values pinned by hand in the slicer. Not measurements - they have no
        # raw number behind them - so they live beside the journal rather than
        # in it, and they are laid over the computed fields on the way out.
        self.manual = {}
        # Permission to write into Orca is deliberately process-local.  Never
        # trust a value carried by an old or hand-edited config.json.
        self.orca_write_approved = False

    # ------------------------------------------------------------- setup

    def choose_material(self):
        materials = scales.materials(self.scales)
        items = [(key, "%-8s база: %s" % (key, entry["base"]))
                 for key, entry in materials.items()]
        return c.menu("Материал", items)

    def choose_spool(self):
        vendors = self.scales.get("vendors", [])
        previous = [(spool, day) for material, spool, day
                    in journal.previous_spools() if material == self.material]
        items = [(spool, "%-28s калибровалась %s" % (spool, day))
                 for spool, day in previous]
        items.append(("__new__", "Новая катушка"))
        chosen = c.menu("Катушка", items)
        if chosen != "__new__":
            return chosen

        brands = [(v, v) for v in vendors] + [("__other__", "Другой производитель")]
        brand = c.menu("Производитель", brands)
        if brand == "__other__":
            brand = c.ask_text("Производитель")
        label = c.ask_text("Название с этикетки (например «Matte PLA»)")
        raw = "%s %s" % (brand, label)
        try:
            return names.safe_name(raw)
        except names.UnsafeName as e:
            c.bad("Такое имя использовать нельзя: %s" % e)
            return self.choose_spool()

    def load_run(self):
        """Continue a run already started, or begin one for today."""
        root = paths.spools_dir(create=not self.dry_run)
        existing = sorted((d for d in os.listdir(root)
                           if os.path.isdir(os.path.join(root, d))
                           and (d.endswith(" " + self.spool)
                                or (" " + self.spool + " [") in d)),
                          reverse=True) if os.path.isdir(root) else []
        selected = None
        loaded_measurements = {}
        loaded_run_id = None
        incompatible = 0
        for folder_name in existing:
            candidate = os.path.join(root, folder_name)
            path = os.path.join(candidate, "measurements.json")
            if not os.path.exists(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
            except (OSError, ValueError):
                continue
            if (isinstance(payload, dict)
                    and payload.get("schema") == run_context.SCHEMA
                    and isinstance(payload.get("measurements"), dict)):
                saved_context = payload.get("context") or {}
                if not run_context.matches(saved_context, self.context):
                    incompatible += 1
                    continue
                loaded_measurements = payload.get("measurements") or {}
                loaded_run_id = payload.get("run_id") or None
            elif (isinstance(payload, dict)
                  and not any(key in payload for key in
                              ("schema", "context", "measurements", "run_id"))
                  and run_context.legacy_is_compatible(self.context)):
                loaded_measurements = payload
            else:
                incompatible += 1
                continue
            selected = folder_name
            break

        folder_name = selected or (
            names.spool_folder_name(self.spool) + " " +
            run_context.folder_suffix(self.context))
        self.folder = names.safe_join(root, folder_name)
        if not self.dry_run:
            os.makedirs(self.folder, exist_ok=True)
        self.measurements = loaded_measurements
        self.run_id = loaded_run_id or uuid.uuid4().hex
        self.context_changed_from = incompatible
        return self.folder

    def save_measurements(self):
        if self.dry_run:
            return
        path = os.path.join(self.folder, "measurements.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "schema": run_context.SCHEMA,
                "run_id": self.run_id,
                "context": self.context,
                "measurements": self.measurements,
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)

    # ---------------------------------------------------------- pinned by hand

    def manual_path(self):
        return os.path.join(self.folder, "manual.json")

    def load_manual(self):
        self.manual = {}
        path = self.manual_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.manual = {str(k): str(v) for k, v in loaded.items()}
            except (OSError, ValueError):
                self.manual = {}

    def save_manual(self):
        if self.dry_run:
            return
        path = self.manual_path()
        if not self.manual:
            if os.path.exists(path):
                os.remove(path)
            return
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.manual, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)

    def with_manual(self, fields):
        """Computed fields with anything pinned by hand laid over the top."""
        merged = dict(fields or {})
        merged.update(self.manual)
        return merged

    def owned_fields(self):
        owned = set()
        for test in self.tests:
            owned.update(test.get("fields") or ())
        if "nozzle_temperature" in owned:
            owned.add("nozzle_temperature_initial_layer")
        return owned

    def reconcile_with_slicer(self, fields):
        """Show where the preset disagrees with the journal and settle it.

        Orca keeps presets in memory and writes them out when it closes, so a
        change made in an open slicer is not on disk yet. Nothing can be done
        about that from here beyond saying so when it bites.
        """
        try:
            targets = self.preset_targets()
        except Exception:
            # No spool name yet, or nothing usable to build a path from. There
            # is simply no preset to compare against, which is not an error.
            return False
        current = presets.read_current(targets, self.owned_fields())
        gaps = presets.differences(self.with_manual(fields), current)
        if not gaps:
            return False
        c.say("")
        c.head("Пресет в слайсере разошёлся с расчётом")
        c.dim("  Похоже, эти поля правились руками в Orca. Калибратор "
              "пересобирает пресет целиком,")
        c.dim("  поэтому без ответа он их перезапишет.")
        changed = False
        for field, (in_slicer, ours) in sorted(gaps.items()):
            c.say("")
            c.say("  %-34s в слайсере %s · расчёт %s" % (field, in_slicer, ours))
            if c.ask_yes("  Оставить значение из слайсера?", default=True):
                self.manual[field] = in_slicer
                c.ok("  закреплено вручную: %s" % in_slicer)
            else:
                self.manual.pop(field, None)
                c.dim("  вернём расчётное: %s" % ours)
            changed = True
        return changed

    def release_manual(self, test):
        """A fresh measurement releases a pin: that is what it was taken for."""
        for field in test.get("fields") or ():
            if field not in self.manual:
                continue
            c.warn("  Поле %s закреплено вручную: %s. Только что его измерили."
                   % (field, self.manual[field]))
            if c.ask_yes("  Снять закрепление и взять замер?", default=True):
                self.manual.pop(field, None)
                self.save_manual()
            else:
                c.dim("  оставили ручное — замер записан, но в пресет не пойдёт")

    # ------------------------------------------------------------ plates

    def plate_menu(self, computed_by_test):
        items = []
        for test in self.tests:
            key = test["key"]
            shown = computed_by_test.get(key)
            pinned = any(f in self.manual for f in test.get("fields") or ())
            if key in self.measurements:
                mark = "[x] " + (shown or "внесено")
            elif shown:
                # A value with no measurement under it: pinned by hand, or
                # carried over from an older preset.
                mark = "[·] " + shown
            else:
                mark = "[ ] —"
            if pinned and shown:
                mark += " · вручную"
            items.append((key, "плита %s · %-14s %s" % (test["order"], key, mark)))
        items.append(("__all__", "Пройти все плиты по порядку"))
        items.append(("__finish__", "Показать итог и выйти"))
        items.append(("__quit__", "Выйти"))
        return c.menu("Что вносим?", items)

    def prepare_plate(self, test, fields_so_far):
        """Return only project-owned geometry that is safe to reopen.

        Orca's dynamic wizard modes are intentionally not represented by a
        saved 3MF: reopening one loses the calibration parameters silently.
        Those tests must be started live from Orca's Calibration menu.
        """
        file_template = test.get("file")
        if not file_template:
            return None
        # Only the project-owned shrinkage bar is safe to reopen.  Orca's five
        # wizard tests must remain in the live session that created them.
        filename = file_template.format(material=self.material).split("/")[-1]
        if filename in templates_mod.FROM_WIZARD:
            return None
        if filename in templates_mod.GENERATED:
            shipped = os.path.join(paths.templates_dir(), self.material, filename)
            return shipped if os.path.exists(shipped) else None
        return None

    def enter_plate(self, test, plate_path=None):
        """One plate's screen. True if a measurement was accepted."""
        params = test.get("params") or {}
        c.head("Плита %s · %s" % (test["order"], test["key"]))
        if test["key"] == "flow" and "ceiling" in params:
            c.say("  шкала: -%s → %s, шаг %s" % (
                params["ceiling"], params["ceiling"], params.get("step", "?")))
        elif "start" in params:
            end = params.get("end")
            if end is None and "step_per_mm" in params:
                end = params.get("ceiling", params["start"] +
                                 params["step_per_mm"] * 40)
            c.say("  шкала: %s → %s, шаг %s" % (
                params["start"], "?" if end is None else end,
                params.get("step", params.get("step_per_mm"))))
        if params.get("unverified"):
            c.warn("шкала не выверена на своей печати — сверь с башней "
                   "и поправь scales.json")

        for number, step in enumerate(test.get("steps", []), start=1):
            c.say("  %d. %s" % (number, step))

        if plate_path and os.path.exists(plate_path):
            if self.dry_run:
                c.dim("сухой прогон — модель найдена; Orca не открывается")
            else:
                c.say("  открываю: %s" % os.path.basename(plate_path))
                if not orca.open_file(plate_path):
                    c.warn("Не открылось — найди файл сам: %s" % plate_path)
        else:
            c.warn("Запусти тест в OrcaSlicer: %s" % test["print_via"])
            c.dim("Используй показанные выше диапазон и шаг. Сохранённую башню")
            c.dim("повторно не открывай: обычный 3MF не хранит режим мастера Orca.")

        measurement = c.ask_number(test["question"], test.get("hint"),
                                   self.measurements.get(test["key"]))
        if measurement is None:
            self.measurements.pop(test["key"], None)
            c.dim("Замер стёрт, поле останется от базы.")
            return False

        try:
            new, why = scales.compute(test, measurement, self.base_values)
        except formulas.MeasurementOutOfRange as e:
            c.bad(str(e))
            c.dim("Замер не принят.")
            return False

        self.measurements[test["key"]] = measurement
        summary = ", ".join("%s = %s" % (field, formulas.format_field(field, value))
                            for field, value in sorted(new.items()))
        c.say("  %s%s%s   %s(%s)%s" % (c.GREEN, summary, c.RESET, c.DIM, why, c.RESET))
        if test.get("after"):
            if self.dry_run:
                c.dim("в реальном прогоне: %s" % test["after"])
            else:
                c.say("  %s→ %s%s" % (c.YELLOW, test["after"], c.RESET))
        return True

    # ------------------------------------------------------------ preset

    def preset_targets(self):
        preset_name = run_context.preset_name(self.spool, self.context)
        return [os.path.join(d, preset_name + ".json")
                for d in orca.filament_dirs()]

    def save_preset(self, fields, ask=True):
        """Write the preset, with the path shown and confirmed first."""
        if not fields:
            return None
        if self.dry_run:
            c.dim("сухой прогон — пресет не записан")
            return None

        targets = self.preset_targets()
        steps = presets.plan(None, targets)
        # ``ask=False`` means "do not repeat the question after every plate",
        # not "write without permission".  Approval is held only on this
        # Session object, so even an old or hand-edited config cannot bypass
        # the first confirmation of a new run.
        needs_permission = ask or not self.orca_write_approved
        if needs_permission:
            c.say("")
            c.say("  Пресет будет записан:")
            c.say(presets.describe_plan(steps))
            if any(action == "replace" for _, action in steps):
                c.dim("Прежние версии сохраняются в %s" % paths.preset_backups_dir())
            if not c.ask_yes("Записать?", default=True):
                c.dim("Не тронул.")
                return None

        # Close Orca BEFORE writing: it holds presets in memory and may write
        # its own copy back on exit. Always asked, never forced.
        if orca.is_running():
            c.say("")
            c.dim("OrcaSlicer открыта. Она держит пресеты в памяти и читает их "
                  "только при старте, поэтому пресет подхватится лишь после "
                  "перезапуска.")
            if c.ask_yes("Закрыть Orca? (несохранённые проекты она спросит сама)",
                         default=True):
                if orca.request_close():
                    c.dim("Orca закрыта.")
                else:
                    c.warn("Orca не закрылась — возможно, спрашивает про "
                           "несохранённый проект.")
                    c.dim("Закрой её сама и повтори, либо продолжай — пресет "
                          "запишется, но подхватится только после перезапуска.")
                    if not c.ask_yes("Продолжить запись?", default=False):
                        return None

        preset_name = run_context.preset_name(self.spool, self.context)
        compatible = orca.compatible_printers(
            nozzle=self.context.get("nozzle", "0.4"),
            machine_preset=self.context.get("machine_preset") or None,
            backend=self.context.get("firmware_backend") or None)
        if not compatible:
            c.bad("Выбранный профиль принтера больше не найден в OrcaSlicer.")
            c.dim("Пресет не записан. Снова запусти Setup.cmd и выбери профиль.")
            return None
        preset = presets.build(
            preset_name, self.base, fields,
            compatible_printers=compatible,
            vendor=names.vendor_of(self.spool, self.scales.get("vendors", [])),
            version=presets.preset_version(orca.filament_dirs()))

        try:
            written, backups = presets.write_all(preset, targets)
        except presets.PresetWriteError as e:
            c.bad(str(e))
            c.dim("Исходный файл не тронут.")
            return None

        for path in written:
            c.ok("записан: %s" % path)
        for backup in backups:
            c.dim("прежний сохранён: %s" % backup)

        self.orca_write_approved = True

        journal.record(journal.build_row(
            self.material, self.spool, self.base, fields,
            context=self.context, run_id=self.run_id))
        c.dim("строка ушла в %s" % paths.journal_path())

        # The only unprompted place the support note may appear: right after a
        # preset was successfully saved. Never on an error, never in a dry run.
        support.maybe_show(printer=c.say, dry_run=self.dry_run)
        return written

    # ------------------------------------------------------------- run

    def run(self):
        materials = scales.materials(self.scales)
        self.material = self.material or self.choose_material()
        entry = materials[self.material]
        self.base = entry["base"]

        install = self.cfg.get("orca_install_dir") or orca.find_installation()
        if not install:
            c.bad("OrcaSlicer не найдена. Запусти Setup.cmd.")
            return 1
        self.profiles = orca.collect_system_filaments(orca.system_profiles_root(install))
        if self.base not in self.profiles:
            c.bad("Базовый профиль «%s» не найден в %s"
                  % (self.base, orca.system_profiles_root(install)))
            return 1
        self.base_values = {"filament_flow_ratio":
                            orca.inherited_value(self.profiles, self.base,
                                                 "filament_flow_ratio")}

        self.spool = self.spool or self.choose_spool()
        self.load_run()
        self.tests = scales.tests_for(self.scales, self.material)
        self.load_manual()

        c.say("\n%s%s · %s%s" % (c.BOLD, self.spool, self.material, c.RESET))
        c.say("База: %s" % self.base)
        drying = entry.get("drying") or {}
        if drying:
            c.say("Сушка перед стартом: %s °C, %s ч"
                  % (drying.get("temperature"), drying.get("hours")))
        if self.dry_run:
            c.warn("СУХОЙ ПРОГОН — ничего не записывается.")
        if self.measurements:
            c.dim("Найден начатый прогон: %s" % os.path.basename(self.folder))
        elif self.context_changed_from:
            c.warn("Прежний прогон этой катушки относится к другой прошивке, "
                   "соплу или профилю.")
            c.dim("Он сохранён без изменений; для текущего контекста начат новый.")

        try:
            return self._loop()
        except c.Cancelled:
            self.save_measurements()
            c.say("\nПрервано. Уже введённые замеры сохранены.")
            return 1

    def _loop(self):
        first_pass = True
        while True:
            fields, _, errors = scales.compute_all(self.tests, self.measurements,
                                                   self.base_values)
            if first_pass:
                first_pass = False
                if self.reconcile_with_slicer(fields):
                    self.save_manual()
            fields = self.with_manual(fields)
            by_test = {}
            for test in self.tests:
                shown = [formulas.format_field(f, fields[f])
                         for f in test["fields"] if f in fields]
                if shown:
                    by_test[test["key"]] = " / ".join(shown)
            for key, text in errors.items():
                by_test[key] = "ошибка: " + text

            choice = self.plate_menu(by_test)

            if choice == "__quit__":
                self.save_measurements()
                if self.dry_run:
                    c.say("\nСухой прогон завершён. Ничего не записано.")
                elif not self.orca_write_approved:
                    c.say("\nГотово. Замеры сохранены. Пресет и журнал не записаны.")
                else:
                    c.say("\nГотово. Пресет и журнал обновлены после каждого замера.")
                return 0
            if choice == "__finish__":
                break

            queue = (self.tests if choice == "__all__"
                     else [t for t in self.tests if t["key"] == choice])
            for test in queue:
                fields_now, _, _ = scales.compute_all(self.tests, self.measurements,
                                                      self.base_values)
                plate = self.prepare_plate(test, self.with_manual(fields_now))
                accepted = self.enter_plate(test, plate)
                self.save_measurements()
                if not accepted:
                    continue
                self.release_manual(test)
                fields_now, _, _ = scales.compute_all(self.tests, self.measurements,
                                                      self.base_values)
                self.save_preset(self.with_manual(fields_now), ask=False)

        fields, _, _ = scales.compute_all(self.tests, self.measurements,
                                          self.base_values)
        fields = self.with_manual(fields)
        if not fields:
            c.say("\nНи одного замера — писать нечего.")
            return 0

        c.head("Что получится")
        c.say("  %-34s %10s  →  %10s" % ("поле", "база", "станет"))
        for field in sorted(fields):
            was = orca.inherited_value(self.profiles, self.base, field)
            c.say("  %-34s %10s  →  %s%10s%s"
                  % (field, "—" if was is None else str(was), c.BOLD,
                     formulas.format_field(field, fields[field]), c.RESET))

        # If a plate was accepted in this process, the current fields were
        # already written.  Otherwise this is the first write attempt and
        # save_preset() will still ask because this process has no approval.
        written = None
        if not self.orca_write_approved:
            written = self.save_preset(fields, ask=False)
        if self.dry_run:
            c.say("\nСухой прогон завершён. Ничего не записано.")
        elif self.orca_write_approved or written:
            c.say("")
            c.say("OrcaSlicer читает пресеты при старте — перезапусти её, чтобы увидеть.")
        return 0


def main(material=None, spool=None, dry_run=False):
    cfg = config_mod.load_or_default()
    try:
        data = scales.load()
    except scales.ScalesError as e:
        c.bad(str(e))
        return 1
    session = Session(cfg, data, dry_run=dry_run)
    if material and material in scales.materials(data):
        session.material = material
    if spool:
        try:
            session.spool = names.safe_name(spool)
        except names.UnsafeName as e:
            c.bad("Имя катушки использовать нельзя: %s" % e)
            return 1
    try:
        return session.run()
    except KeyboardInterrupt:
        c.say("\nПрервано.")
        return 1
