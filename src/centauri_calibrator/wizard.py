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
    version = orca.installed_version(install)
    if version:
        c.ok("Версия профилей Elegoo: %s" % version)
    else:
        c.warn("Версию определить не удалось.")
    c.dim("Проект проверен на OrcaSlicer %s. Другие версии не тестировались."
          % orca.TESTED_ORCA_VERSION)
    return version or ""


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


def step_machine_preset(cfg):
    c.head("5. Профиль принтера")
    system_name, matches = orca.centauri_machine_presets()
    c.dim("Системный профиль: %s" % system_name)

    if not matches:
        c.warn("Своих пресетов принтера нет — будет использован системный.")
        c.dim("Свой пресет нужен, если хочешь отправлять печать по сети: "
              "адрес принтера хранится только в нём.")
        return system_name

    if len(matches) == 1:
        name = matches[0][1]["name"]
        c.ok("Найден один: %s" % name)
        return name

    c.warn("Своих пресетов несколько — выбери, на каком калибруешь.")
    items = [(node["name"], "%s   %s" % (node["name"], os.path.basename(path)))
             for path, node in matches]
    previous = cfg.get("machine_preset")
    if previous and any(k == previous for k, _ in items):
        items.insert(0, (previous, "%s   (был выбран прежде)" % previous))
    return c.menu("Профиль принтера", items)


def step_print_host(cfg):
    """The address is optional, and its absence is not an error.

    Plenty of people slice to a USB stick. Treating "no network printing" as a
    broken setup would send them looking for a problem they do not have.
    """
    c.head("6. Адрес принтера (необязательно)")
    found = orca.find_print_host()
    if found:
        c.ok("Уже настроен в Orca: %s" % found["print_host"])
        if c.ask_yes("Использовать его для отправки плит по сети?", default=True):
            return found["print_host"]
        return ""

    c.dim("В Orca адрес не настроен. Это нормально: без него всё работает, "
          "плиты просто не отправляются по сети.")
    previous = cfg.get("print_host")
    if previous:
        c.dim("Прежде был задан: %s" % previous)
    if not c.ask_yes("Задать адрес принтера?", default=False):
        return ""
    return c.ask("IP-адрес принтера", default=previous or None)


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
    for directory in (paths.spools_dir(), paths.generated_plates_dir(),
                      paths.preset_backups_dir(), paths.logs_dir()):
        os.makedirs(directory, exist_ok=True)
    c.ok(base)
    c.dim("Журнал, замеры, персональные плиты и резервные копии пресетов — здесь. "
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

        version = step_version(install)
        step_system_profiles(install)
        step_user_dirs()
        machine_preset = step_machine_preset(cfg)
        print_host = step_print_host(cfg)
        step_write_access()
        step_data_dir()

        cfg.update({
            "orca_install_dir": install,
            "orca_version": version,
            "machine_preset": machine_preset,
            "print_host": print_host,
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
