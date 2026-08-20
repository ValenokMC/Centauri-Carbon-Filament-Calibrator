# -*- coding: utf-8 -*-
"""Calibration plates: reading templates, writing personal copies.

The model this project uses, and the reason for it:

  * a template is opened **read-only**, always. It is shared by every spool of
    a material and by every user of the release, and a template that picks up
    one person's printer address is exactly the leak this project exists to
    avoid.
  * a personal copy is written into the user's own data directory, with their
    machine preset, their measured values so far, and - only if they have one -
    their own print_host.
  * nothing personal ever travels in the other direction.

Without the personal copy the plate opens in the slicer on the base profile and
prints with the base filament's temperature and flow. A measurement taken from
that describes a generic filament, not the spool in the machine.
"""
import json
import os
import re
import zipfile

from . import formulas, names, paths


CONFIG_ENTRY = "Metadata/project_settings.config"
MODEL_SETTINGS_ENTRY = "Metadata/model_settings.config"

# Keys that identify a person or a machine rather than a print. Stripped from
# anything that is about to become a public template.
PERSONAL_KEYS = ("print_host", "printhost_apikey", "printhost_authorization_type",
                 "printhost_cafile", "printhost_port", "printhost_ssl_ignore_revoke",
                 "print_host_webui", "bbl_use_printhost")


class PlateError(Exception):
    pass


def read_entries(path):
    """Every entry of a .3mf, as {name: bytes}. Opens read-only."""
    try:
        with zipfile.ZipFile(path) as z:
            return {name: z.read(name) for name in z.namelist()}
    except (OSError, zipfile.BadZipFile) as e:
        raise PlateError("cannot read %s: %s" % (path, e))


def write_entries(path, entries):
    """Write a .3mf atomically: build beside the target, then replace."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp = os.path.join(directory, ".%s.tmp" % os.path.basename(path))
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise PlateError("cannot write %s: %s" % (path, e))
    return path


def read_config(entries):
    raw = entries.get(CONFIG_ENTRY)
    if raw is None:
        raise PlateError("%s is missing - not an OrcaSlicer project" % CONFIG_ENTRY)
    try:
        return json.loads(raw)
    except ValueError as e:
        raise PlateError("%s is not valid JSON: %s" % (CONFIG_ENTRY, e))


def store_config(entries, config):
    entries[CONFIG_ENTRY] = json.dumps(config, ensure_ascii=False,
                                       indent=1).encode("utf-8")


# ------------------------------------------------------------- sanitising

def strip_personal(config):
    """Remove every key that identifies a person or their network.

    Returns (config, removed_keys). Used when a template is created, and
    asserted on by the safety scanner before release.
    """
    removed = []
    for key in PERSONAL_KEYS:
        if key in config:
            removed.append(key)
            config.pop(key)
    return config, removed


def sanitise_template(source, target, filament_settings_id=None,
                      printer_settings_id=None):
    """Copy a .3mf into a publishable template, with all personal data gone.

    The printer and filament preset ids are replaced with neutral system names.
    A preset id saved by a real user names one person's setup - their printer
    profile, their spool - and shipping it would both leak and break: nobody
    else has a preset by that name, so the slicer would silently substitute an
    arbitrary one with arbitrary temperatures.
    """
    entries = read_entries(source)
    config = read_config(entries)
    config, removed = strip_personal(config)
    if printer_settings_id:
        config["printer_settings_id"] = printer_settings_id
    if filament_settings_id:
        config["filament_settings_id"] = (
            [filament_settings_id] if isinstance(config.get("filament_settings_id"), list)
            else filament_settings_id)
    store_config(entries, config)
    write_entries(target, entries)
    return removed


# --------------------------------------------------- personalising a plate

def personalise(template, spool, fields, folder=None, network=None,
                machine_preset=None):
    """Build this user's copy of a plate. The template is not modified.

    ``fields`` are the values measured so far, so each plate prints on the
    values found by the previous ones - which is the whole reason the tests run
    in order.
    """
    if not os.path.exists(template):
        raise PlateError("template not found: %s" % template)

    folder = folder or paths.generated_plates_dir()
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, os.path.basename(template))

    entries = read_entries(template)
    config = read_config(entries)
    flow_before = float((config.get("filament_flow_ratio") or ["1"])[0])

    config["filament_settings_id"] = [names.safe_name(spool)]
    if machine_preset:
        config["printer_settings_id"] = machine_preset
    # Only into the personal copy, and only if the user has one configured.
    if network:
        config.update(network)

    if os.path.basename(template).startswith("5_retraction"):
        # Orca reads the user's process first and then lays the project's
        # settings snapshot on top. An empty post_process from the project
        # therefore switched off the process's working command. In a personal
        # copy the key must be absent, so Orca processes its own temporary
        # G-code before sending.
        config.pop("post_process", None)

    for field, value in (fields or {}).items():
        formatted = formulas.format_field(field, value)
        config[field] = ([formatted] if isinstance(config.get(field), list)
                         else formatted)

    flow_after = float((config.get("filament_flow_ratio") or ["1"])[0])
    store_config(entries, config)

    # On the flow plate every tile carries its own ratio, computed against the
    # previous base. Change the base and they must be recomputed, or the
    # printed labels no longer describe what is being printed.
    settings = entries.get(MODEL_SETTINGS_ENTRY)
    if settings and flow_after != flow_before and flow_after:
        entries[MODEL_SETTINGS_ENTRY] = _rescale_flow_tiles(settings, flow_after)

    write_entries(target, entries)
    return target


def _rescale_flow_tiles(raw, flow_base):
    chunks = re.split(r"(?=<object )", raw.decode("utf-8"))
    for index, chunk in enumerate(chunks):
        found = re.search(r'key="name" value="flowrate_([^"]+)"', chunk)
        if not found:
            continue
        offset = float(found.group(1).replace("m", "-") or 0)
        share = (flow_base + offset) / flow_base
        chunks[index] = re.sub(
            r'(key="print_flow_ratio" value=")[0-9.]+(")',
            lambda m: m.group(1) + "{:.6f}".format(share) + m.group(2), chunk)
    return "\n".join(chunks).encode("utf-8")


# ------------------------------------------------------------- inspection

TEXT_SUFFIXES = (".xml", ".config", ".json", ".rels", ".model", ".gcode", ".txt")


def inspect(path):
    """What a .3mf contains, for the safety scanner and the doctor command."""
    entries = read_entries(path)
    try:
        config = read_config(entries)
    except PlateError:
        config = {}
    return {
        "entries": sorted(entries),
        "print_host": config.get("print_host"),
        "printer_settings_id": config.get("printer_settings_id"),
        "filament_settings_id": config.get("filament_settings_id"),
        "printer_model": config.get("printer_model"),
    }


def template_path(templates_root, material, filename_template):
    """Resolve "{material}/1_temperature.3mf" against the templates root."""
    relative = filename_template.format(material=material)
    return os.path.join(templates_root, *relative.split("/"))
