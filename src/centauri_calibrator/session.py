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

from . import config as config_mod
from . import console as c
from . import formulas, journal, names, orca, paths, presets, scales
from . import templates as templates_mod
from . import support


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
        existing = sorted(d for d in os.listdir(root)
                          if os.path.isdir(os.path.join(root, d))
                          and d.endswith(" " + self.spool)) if os.path.isdir(root) else []
        folder_name = existing[-1] if existing else names.spool_folder_name(self.spool)
        self.folder = names.safe_join(root, folder_name)
        if not self.dry_run:
            os.makedirs(self.folder, exist_ok=True)

        path = os.path.join(self.folder, "measurements.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.measurements = json.load(f)
            except (OSError, ValueError):
                self.measurements = {}
        return self.folder

    def save_measurements(self):
        if self.dry_run:
            return
        path = os.path.join(self.folder, "measurements.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.measurements, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # ------------------------------------------------------------ plates

    def plate_menu(self, computed_by_test):
        items = []
        for test in self.tests:
            key = test["key"]
            if key in self.measurements:
                shown = computed_by_test.get(key) or "внесено"
                mark = "[x] " + shown
            else:
                mark = "[ ] —"
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
        return [os.path.join(d, self.spool + ".json")
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

        preset = presets.build(
            self.spool, self.base, fields,
            compatible_printers=orca.compatible_printers(nozzle=self.cfg.get("nozzle", "0.4")),
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

        journal.record(journal.build_row(self.material, self.spool, self.base, fields))
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

        try:
            return self._loop()
        except c.Cancelled:
            self.save_measurements()
            c.say("\nПрервано. Уже введённые замеры сохранены.")
            return 1

    def _loop(self):
        while True:
            fields, _, errors = scales.compute_all(self.tests, self.measurements,
                                                   self.base_values)
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
                plate = self.prepare_plate(test, fields_now)
                accepted = self.enter_plate(test, plate)
                self.save_measurements()
                if not accepted:
                    continue
                fields_now, _, _ = scales.compute_all(self.tests, self.measurements,
                                                      self.base_values)
                self.save_preset(fields_now, ask=False)

        fields, _, _ = scales.compute_all(self.tests, self.measurements,
                                          self.base_values)
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
