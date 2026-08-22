# -*- coding: utf-8 -*-
"""Entry point: python -m centauri_calibrator [run|setup|doctor|...]"""
import sys

from . import console as c


USAGE = """Использование:
  python -m centauri_calibrator            калибровать
  python -m centauri_calibrator setup      мастер настройки
  python -m centauri_calibrator doctor     диагностика окружения, ничего не менять
  python -m centauri_calibrator dry-run    пройти диалог, ничего не записывая
  python -m centauri_calibrator templates  объяснить работу моделей OrcaSlicer
  python -m centauri_calibrator about      о проекте и как поддержать автора
  python -m centauri_calibrator where      открыть каталог с данными

Ключи для run и dry-run:
  --material PLA        сразу выбрать материал
  --spool "eSUN PLA"    сразу выбрать катушку
"""


def _parse(argv):
    material = spool = None
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item == "--material" and rest:
            material = rest.pop(0)
        elif item == "--spool" and rest:
            spool = rest.pop(0)
    return material, spool


def cmd_doctor():
    """Read-only diagnosis. Writes nothing, closes nothing, opens nothing."""
    from . import config as config_mod
    from . import orca, paths, plates
    from . import templates as templates_mod
    import os

    c.say("%s=== Диагностика ===%s" % (c.BOLD, c.RESET))

    c.head("Настройка")
    try:
        cfg = config_mod.load()
        for line in config_mod.summary(cfg):
            c.say("  " + line)
    except config_mod.ConfigError as e:
        c.warn(str(e).splitlines()[0])
        cfg = config_mod.load_or_default()

    c.head("OrcaSlicer")
    report = orca.survey()
    if report["install_dir"]:
        c.ok("установлена: %s" % report["install_dir"])
        c.say("     версия профилей: %s (проект проверен на %s)"
              % (report["version"] or "неизвестна", report["tested_version"]))
        c.say("     системных профилей филамента: %d" % report["system_profiles"])
    else:
        c.bad("не найдена")

    c.head("Каталоги пользователя Orca")
    for directory in report["account_dirs"]:
        c.say("  %s" % directory)

    c.head("Пресеты принтера")
    if report["machine_presets"]:
        for name in report["machine_presets"]:
            c.ok(name)
    else:
        c.warn("своих пресетов нет — будет использован системный")
    c.head("Данные")
    c.say("  %s" % paths.data_dir(create=False))
    for label, directory in (("катушки", paths.spools_dir(create=False)),
                             ("резервные копии", paths.preset_backups_dir(create=False))):
        count = len(os.listdir(directory)) if os.path.isdir(directory) else 0
        c.say("     %-16s %d" % (label, count))

    c.head("Собственные модели")
    template_report = templates_mod.status()
    ready = sum(len(state["have"]) for state in template_report.values())
    total = sum(len(state["have"]) + len(state["missing"])
                for state in template_report.values())
    c.say("  моделей усадки: %d из %d" % (ready, total))
    for material, state in template_report.items():
        c.say("     %-9s %d из %d" % (
            material, len(state["have"]),
            len(state["have"]) + len(state["missing"])))
    c.say("  остальные тесты: запускаются из живого мастера OrcaSlicer")
    if ready == 0:
        c.warn("модели усадки отсутствуют — переустанови архив проекта")

    return 0 if report["install_dir"] else 1


def cmd_about():
    from . import support
    for line in support.about_lines():
        c.say(line)
    c.say("")
    if c.ask_yes("Открыть страницу поддержки в браузере?", default=False):
        if support.open_tribute(confirm=True):
            c.ok("Открыл.")
        else:
            c.warn("Не открылось — ссылка выше.")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    action = argv[0] if argv and not argv[0].startswith("-") else "run"

    if action in ("-h", "--help", "help"):
        c.say(USAGE)
        return 0
    if action == "setup":
        from . import wizard
        return wizard.main(argv[1:])
    if action == "doctor":
        return cmd_doctor()
    if action == "about":
        return cmd_about()
    if action == "templates":
        from . import templates as templates_mod
        return templates_mod.main(argv[1:])
    if action == "where":
        from . import paths
        c.say(paths.data_dir())
        return 0
    if action in ("run", "dry-run"):
        from . import session
        material, spool = _parse(argv[1:])
        return session.main(material=material, spool=spool,
                            dry_run=(action == "dry-run"))
    c.say(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
