# -*- coding: utf-8 -*-
"""First-run setup: find OrcaSlicer, find the profiles, confirm before writing.

Nothing here writes into the OrcaSlicer tree. The wizard's job is to find
things, check that they are usable, and record what it found. The first actual
write happens during a calibration run, after its own confirmation.
"""
import os

from . import config as config_mod
from . import console as c
from . import orca, paths, presets, support


def step_find_orca(cfg):
    c.head("1. OrcaSlicer")
    install = orca.find_installation()
    if not install and cfg.get("orca_install_dir"):
        install = cfg["orca_install_dir"] if os.path.isdir(
            cfg["orca_install_dir"]) else None

    if install:
        c.ok("Найден: %s" % install)
    else:
        c.bad("OrcaSlicer не найден в обычных местах установки.")
        for candidate in orca.DEFAULT_INSTALL_DIRS:
            if candidate:
                c.dim("проверено: %s" % candidate)
        if not c.ask_yes("Указать путь вручную?", default=True):
            return None
        while True:
            manual = c.ask("Папка OrcaSlicer")
            if os.path.isdir(os.path.join(manual, "resources", "profiles")):
                install = manual
                c.ok("Подходит: %s" % install)
                break
            c.bad("Здесь нет resources/profiles — это не папка OrcaSlicer.")
            if not c.ask_yes("Попробовать другой путь?", default=True):
                return None
    return install


def step_version(install):
    c.head("2. Версия")
    app_version = orca.application_version(install)
    bundle_version = orca.profile_bundle_version(install)
    if app_version:
        c.ok("OrcaSlicer: %s" % app_version)
    else:
        c.warn("Версию приложения определить не удалось.")
    if bundle_version:
        c.ok("Пакет профилей Elegoo: %s" % bundle_version)
    else:
        c.warn("Версию пакета Elegoo определить не удалось.")
    c.dim("Проект проверен на OrcaSlicer %s. Другие версии не тестировались."
          % orca.TESTED_ORCA_VERSION)
    return app_version or "", bundle_version or ""


def step_system_profiles(install):
    c.head("3. Системные профили Elegoo")
    profiles = orca.collect_system_filaments(orca.system_profiles_root(install))
    if profiles:
        c.ok("Найдено профилей филамента: %d" % len(profiles))
    else:
        c.bad("Профили Elegoo не найдены — калибровать будет не от чего.")
    return profiles


def step_user_dirs():
    c.head("4. Каталоги пользователя Orca")
    root = orca.user_root()
    c.dim(root)
    accounts = orca.account_dirs()
    for directory in accounts:
        label = os.path.basename(directory)
        kind = "общий" if label == "default" else "аккаунт"
        c.ok("%s: %s" % (kind, label))
    if len(accounts) > 1:
        c.dim("Пресет будет записан во все — какой из них читает Orca, "
              "зависит от того, вошёл ли ты в аккаунт.")
    return accounts


def step_firmware(cfg):
    c.head("5. Прошивка")
    current = cfg.get("firmware_backend")
    items = [
        (orca.BACKEND_STOCK, "Штатная Elegoo (SDCP)"),
        (orca.BACKEND_COSMOS, "OpenCentauri / COSMOS (Moonraker)"),
    ]
    if current in orca.BACKENDS:
        items.insert(0, (current, "%s   (выбрано прежде)" % current))
    return c.menu("Что сейчас установлено", items)


def step_machine_preset(cfg, firmware_backend):
    c.head("6. Профиль принтера")
    system_name, matches = orca.centauri_machine_presets(
        backend=firmware_backend)
    c.dim("Системный профиль: %s" % system_name)

    if not matches:
        if firmware_backend == orca.BACKEND_COSMOS:
            c.bad("Профиль COSMOS/Moonraker для сопла 0.4 не найден.")
            c.dim("Сначала импортируй официальный профиль COSMOS в OrcaSlicer, "
                  "затем снова запусти Setup.cmd.")
            return None, ""
        c.warn("Своих пресетов принтера нет — будет использован системный.")
        synthetic = {"name": system_name, "inherits": system_name}
        return system_name, orca.machine_profile_fingerprint(synthetic)

    if len(matches) == 1:
        node = matches[0][1]
        name = node["name"]
        c.ok("Найден один: %s" % name)
        return name, orca.machine_profile_fingerprint(node)

    c.warn("Своих пресетов несколько — выбери, на каком калибруешь.")
    items = [(orca.machine_profile_fingerprint(node),
              "%s   %s" % (node["name"], os.path.basename(path)))
             for path, node in matches]
    previous = cfg.get("machine_preset")
    previous_fingerprint = cfg.get("machine_fingerprint")
    if previous and previous_fingerprint and any(
            k == previous_fingerprint for k, _ in items):
        items.insert(0, (previous_fingerprint,
                        "%s   (был выбран прежде)" % previous))
    selected = c.menu("Профиль принтера", items)
    for _, node in matches:
        if orca.machine_profile_fingerprint(node) == selected:
            return node["name"], selected
    return None, ""


def step_write_access():
    c.head("7. Права на запись")
    everything_ok = True
    for directory in orca.filament_dirs():
        if presets.can_write(directory):
            c.ok("Записывать можно: %s" % directory)
        else:
            c.bad("Нет доступа на запись: %s" % directory)
            everything_ok = False
    if not everything_ok:
        c.dim("Обычно это значит, что Orca установлена от другого пользователя. "
              "Калибровка будет работать, но пресет придётся переносить вручную.")
    return everything_ok


def step_data_dir():
    c.head("8. Каталог данных")
    base = paths.data_dir()
    for directory in (paths.spools_dir(), paths.preset_backups_dir(),
                      paths.logs_dir()):
        os.makedirs(directory, exist_ok=True)
    c.ok(base)
    c.dim("Журнал, замеры и резервные копии пресетов — здесь. "
          "Ничего из этого не попадает в репозиторий.")
    return base


def run(argv=None):
    c.say("%s=== Настройка калибратора филамента ===%s" % (c.BOLD, c.RESET))
    cfg = config_mod.load_or_default()

    try:
        install = step_find_orca(cfg)
        if not install:
            c.bad("Без OrcaSlicer калибровать нечем. Настройка не завершена.")
            return 1

        app_version, bundle_version = step_version(install)
        step_system_profiles(install)
        step_user_dirs()
        firmware_backend = step_firmware(cfg)
        machine_preset, machine_fingerprint = step_machine_preset(
            cfg, firmware_backend)
        if not machine_preset:
            return 1
        step_write_access()
        step_data_dir()

        cfg.update({
            "orca_install_dir": install,
            # Keep the v1.0 field meaningful for older builds that may read
            # this config, while new builds store both versions explicitly.
            "orca_version": bundle_version,
            "orca_app_version": app_version,
            "profile_bundle_version": bundle_version,
            "firmware_backend": firmware_backend,
            "machine_preset": machine_preset,
            "machine_fingerprint": machine_fingerprint,
            "nozzle": orca.SUPPORTED_NOZZLE,
        })

        c.head("Итог")
        for line in config_mod.summary(cfg):
            c.say("  " + line)

        c.say("")
        c.dim("Запись пресетов в OrcaSlicer выполняется только с твоего "
              "подтверждения, отдельно на каждом прогоне.")
        if not c.ask_yes("\n  Сохранить настройку?", default=True):
            c.say("Ничего не сохранено.")
            return 1
    except c.Cancelled:
        c.say("\nНастройка прервана. Ничего не сохранено.")
        return 1

    path = config_mod.save(cfg)
    c.ok("Настройки записаны: %s" % path)
    support.mark_installed()

    c.say("")
    c.say("%sГотово.%s Калибровать: Калибровать.cmd (или Run.cmd)" % (c.GREEN, c.RESET))
    c.say("Проверить окружение в любой момент: Doctor.cmd")
    return 0


def main(argv=None):
    try:
        return run(argv)
    except KeyboardInterrupt:
        c.say("\nПрервано.")
        return 1
