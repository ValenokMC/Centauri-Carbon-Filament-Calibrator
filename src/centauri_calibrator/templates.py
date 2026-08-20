# -*- coding: utf-8 -*-
"""Building the calibration plates on the user's own machine.

Why this exists instead of shipping ready-made plates.

Five of the six plates per material - temperature, flow, pressure advance, max
flow and retraction - are OrcaSlicer's own calibration models, saved out of its
calibration wizard. They are good models: the blocks carry printed labels and
real test features, bridges, overhangs, stringing transitions. Bare boxes would
be worse in every way, which is why the original workflow used them.

But their licence is not stated anywhere this project can point to, and
redistributing someone else's models on that basis is not something a public
repository should do. So the repository ships the generator and the recipe, and
the plates are built here, on the machine that already has OrcaSlicer installed
and is already entitled to those models.

The one plate that is not Orca's - the shrinkage bar - is generated from
scratch by geometry.py and ships in templates/.
"""
import glob
import os
import re
import shutil
import zipfile

from . import console as c
from . import geometry, orca, paths, plates


# Which plate comes from where.
FROM_WIZARD = {
    "1_temperature.3mf": ("Температурная башня", "Nozzle temperature test"),
    "2_flow.3mf": ("Тест потока (Flow rate)", "Flow rate"),
    "3_pressure_advance.3mf": ("Pressure Advance", "Pressure Advance Test"),
    "4_max_flow.3mf": ("Максимальный объёмный расход", "Max volumetric speed test"),
    "5_retraction.3mf": ("Ретракт", "Retraction test"),
}
GENERATED = {"2b_shrinkage.3mf": "Брусок усадки"}

MATERIALS = ("PLA", "PETG", "PETG-CF", "PETG-GF", "ABS", "ASA", "PA", "TPU")

# A filament preset compatible with ANY printer. Elegoo's own profiles
# ("Generic PLA @Elegoo Centauri" and friends) list their compatible printers
# by name and know nothing of user presets: on someone else's machine the plate
# would be left without a filament and Orca would substitute an arbitrary one,
# with arbitrary temperatures. The values are not changed - they are already
# laid out in the project config - only the name of the base it derives from.
NEUTRAL_FILAMENT = {
    "PLA": "Generic PLA @System",
    "PETG": "Generic PETG @System",
    "PETG-CF": "Generic PETG-CF @System",
    "PETG-GF": "Elegoo PETG-GF @System",
    "ABS": "Generic ABS @System",
    "ASA": "Generic ASA @System",
    "PA": "Generic PA @System",
    "TPU": "Generic TPU @System",
}


def local_templates_dir():
    """Where locally built plates live. Never the repository."""
    d = os.path.join(paths.data_dir(), "templates")
    os.makedirs(d, exist_ok=True)
    return d


def resolve(material, filename):
    """Find a plate: the user's build first, the shipped one second."""
    local = os.path.join(local_templates_dir(), material, filename)
    if os.path.exists(local):
        return local
    shipped = os.path.join(paths.templates_dir(), material, filename)
    if os.path.exists(shipped):
        return shipped
    return None


def status():
    """What is present and what is missing, per material."""
    report = {}
    for material in MATERIALS:
        have, missing = [], []
        for filename in list(FROM_WIZARD) + list(GENERATED):
            (have if resolve(material, filename) else missing).append(filename)
        report[material] = {"have": have, "missing": missing}
    return report


# ------------------------------------------------------------- generated

def build_shrinkage(material, reference_config=None):
    """Generate the shrinkage plate. Entirely our own geometry."""
    parts, expected = geometry.shrinkage_parts()
    target = os.path.join(local_templates_dir(), material, "2b_shrinkage.3mf")

    if reference_config:
        config = dict(reference_config)
        config, _ = plates.strip_personal(config)
        name = NEUTRAL_FILAMENT.get(material)
        if name:
            config["filament_settings_id"] = [name]
        geometry.write_project(target, parts, config,
                               "Калибровка: усадка (%s)" % material)
    else:
        geometry.write_model(target, parts, "Калибровка: усадка (%s)" % material)

    problems = geometry.verify(target, expected)
    return target, problems


# ---------------------------------------------------------- from the wizard

def import_from_wizard(source, material, filename, reference_config=None):
    """Take a project the user saved from Orca's calibration wizard.

    It is sanitised on the way in - print_host and personal preset ids removed -
    so that even the user's own local template holds nothing that would leak if
    they later attached it to a bug report.
    """
    if not os.path.exists(source):
        raise plates.PlateError("файл не найден: %s" % source)
    target = os.path.join(local_templates_dir(), material, filename)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    removed = plates.sanitise_template(
        source, target,
        filament_settings_id=NEUTRAL_FILAMENT.get(material),
        printer_settings_id="%s %s nozzle" % (orca.SUPPORTED_PRINTER_MODEL,
                                              orca.SUPPORTED_NOZZLE))
    return target, removed


def find_saved_projects(search_dirs=None):
    """Look for .3mf files that look like saved wizard output."""
    roots = search_dirs or [
        os.path.join(os.path.expanduser("~"), "Downloads"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
    ]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path in glob.glob(os.path.join(root, "*.3mf")):
            found.append(path)
    return sorted(found)


# ------------------------------------------------------------------ flow

def guide(argv=None):
    c.say("%s=== Сборка калибровочных плит ===%s" % (c.BOLD, c.RESET))
    c.say("")
    c.dim("Пять из шести плит — это модели из мастера калибровки OrcaSlicer.")
    c.dim("Их лицензия нигде явно не указана, поэтому в репозиторий они не")
    c.dim("входят: на твоей машине OrcaSlicer уже установлена, и мастер даёт")
    c.dim("эти модели штатно. Собираем их один раз здесь.")
    c.say("")
    c.say("Подробно: docs/templates.md")

    install = orca.find_installation()
    if not install:
        c.bad("OrcaSlicer не найдена — сначала Setup.cmd.")
        return 1

    reference = _reference_config()

    c.head("Что уже есть")
    report = status()
    for material, state in report.items():
        mark = c.GREEN + "полный" + c.RESET if not state["missing"] else (
            "%d из %d" % (len(state["have"]),
                          len(state["have"]) + len(state["missing"])))
        c.say("  %-9s %s" % (material, mark))

    c.head("1. Плита усадки")
    c.dim("Эта плита наша — генерируется прямо сейчас, ничего скачивать не нужно.")
    if c.ask_yes("Сгенерировать плиты усадки для всех материалов?", default=True):
        for material in MATERIALS:
            target, problems = build_shrinkage(material, reference)
            if problems:
                c.bad("%s: %s" % (material, "; ".join(problems)))
            else:
                c.ok("%s → %s" % (material, target))

    c.head("2. Плиты из мастера OrcaSlicer")
    c.say("  В OrcaSlicer открой меню «Калибровка» и прогони нужный тест.")
    c.say("  Когда мастер построит плиту, сохрани проект: Файл → Сохранить как.")
    c.say("  Затем укажи сохранённый файл здесь.")
    c.say("")
    for filename, (russian, english) in FROM_WIZARD.items():
        c.say("    %-24s %s  (в меню: %s)" % (filename, russian, english))
    c.say("")

    if not c.ask_yes("Импортировать сохранённый проект сейчас?", default=False):
        c.say("")
        c.dim("Можно вернуться к этому позже: Prepare-Templates.cmd")
        return 0

    while True:
        material = c.menu("Для какого материала", [(m, m) for m in MATERIALS])
        which = c.menu("Какая плита", [(f, "%s — %s" % (f, FROM_WIZARD[f][0]))
                                       for f in FROM_WIZARD])
        source = c.ask("Путь к сохранённому .3mf")
        source = source.strip().strip('"')
        try:
            target, removed = import_from_wizard(source, material, which, reference)
        except plates.PlateError as e:
            c.bad(str(e))
            if c.ask_yes("Попробовать снова?", default=True):
                continue
            break
        c.ok("готово: %s" % target)
        if removed:
            c.dim("вычищено из копии: %s" % ", ".join(removed))
        if not c.ask_yes("Импортировать ещё одну?", default=True):
            break

    c.say("")
    c.ok("Плиты готовы. Калибровать: Калибровать.cmd")
    return 0


def _reference_config():
    """The machine configuration, read from the user's own Orca.

    The original workflow kept a saved cube project as the donor for this. That
    is not shipped here for the same licensing reason as the towers, and it does
    not need to be: the configuration can be read from the installation that is
    already on this machine.
    """
    saved = os.path.join(paths.data_dir(), "reference-project.3mf")
    if os.path.exists(saved):
        try:
            entries = plates.read_entries(saved)
            return plates.read_config(entries)
        except plates.PlateError:
            pass
    return None


def adopt_reference(source):
    """Store a project saved from the user's Orca as the configuration donor.

    Sanitised on the way in, and kept in the data directory - never in the
    repository, never published.
    """
    target = os.path.join(paths.data_dir(), "reference-project.3mf")
    removed = plates.sanitise_template(source, target)
    return target, removed


def main(argv=None):
    try:
        return guide(argv)
    except c.Cancelled:
        c.say("\nПрервано.")
        return 1
    except KeyboardInterrupt:
        c.say("\nПрервано.")
        return 1
