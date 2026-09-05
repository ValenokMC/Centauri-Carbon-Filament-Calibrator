# -*- coding: utf-8 -*-
"""Writing the filament preset into OrcaSlicer's profile tree.

This is the one place the program writes outside its own data directory, so it
is the one place that has to be paranoid:

  * the exact path is shown and confirmed before anything happens;
  * the existing file, if any, is copied into preset-backups/ first;
  * the new content is validated as JSON before it goes anywhere;
  * it is written to a temporary file in the same directory and moved into
    place with os.replace, which is atomic on Windows;
  * on any failure the original is still there, untouched.

A half-written preset is worse than no preset: OrcaSlicer refuses to start with
a corrupt profile, and the user has no idea which file to delete.
"""
import datetime
import glob
import json
import os
import shutil
import tempfile

from . import formulas, paths


DEFAULT_VERSION = "2.4.2.0"


class PresetWriteError(Exception):
    """Writing failed. The original file, if there was one, is intact."""


def read_current(targets, fields):
    """What the spool's preset holds right now, as {field: string}.

    The calibrator rebuilds the preset from the journal in full, so anything
    edited by hand in the slicer would be overwritten without a word. Reading
    the file first is what makes it possible to notice and ask instead.

    Only the fields the calibrator owns come back; the rest of the preset is
    none of its business.
    """
    wanted = set(fields or ())
    for path in targets:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                node = json.load(f)
        except (OSError, ValueError):
            return {}
        current = {}
        for field, value in node.items():
            if field not in wanted:
                continue
            if isinstance(value, list):
                value = value[0] if value else None
            if value is not None:
                current[field] = str(value)
        return current
    return {}


def differences(computed, current):
    """{field: (what the slicer has, what we computed)} where they disagree."""
    out = {}
    for field, value in (computed or {}).items():
        was = (current or {}).get(field)
        now = formulas.format_field(field, value)
        if was is not None and was != now:
            out[field] = (was, now)
    return out


def build(name, base, fields, compatible_printers, vendor=None, version=None):
    """An overlay preset: only what was actually measured.

    Everything else is inherited, so an update to the Elegoo profiles does not
    wipe the calibration - and so the diff a user sees is six lines, not six
    hundred.
    """
    preset = {
        "compatible_printers": list(compatible_printers),
        "filament_vendor": vendor or "Generic",
        "from": "User",
        "inherits": base,
        "is_custom_defined": 0,
        "name": name,
        "filament_settings_id": name,
        "version": version or DEFAULT_VERSION,
    }
    for field, value in sorted(fields.items()):
        preset[field] = [formulas.format_field(field, value)]
    if "pressure_advance" in fields:
        preset["enable_pressure_advance"] = ["1"]
    return preset


def preset_version(filament_dirs):
    """Take the version from a preset already on disk, so it matches Orca."""
    for directory in filament_dirs:
        for path in glob.glob(os.path.join(directory, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    version = json.load(f).get("version")
                if version:
                    return version
            except (OSError, ValueError):
                continue
    return DEFAULT_VERSION


def plan(preset, targets):
    """Describe what a write would do, without doing it.

    Returns a list of (path, action) where action is "create" or "replace".
    This is what the confirmation prompt and the dry run both print, so what
    the user is shown and what would happen cannot drift apart.
    """
    return [(path, "replace" if os.path.exists(path) else "create")
            for path in targets]


def describe_plan(steps):
    lines = []
    for path, action in steps:
        verb = "будет заменён" if action == "replace" else "будет создан"
        lines.append("  %s\n     %s" % (path, verb))
    return "\n".join(lines)


def back_up(path, backups=None):
    """Copy an existing preset aside before it is replaced. Returns the copy."""
    if not os.path.exists(path):
        return None
    directory = backups or paths.preset_backups_dir()
    os.makedirs(directory, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = os.path.join(directory, "%s.%s.json" % (
        os.path.splitext(os.path.basename(path))[0], stamp))
    shutil.copy2(path, target)
    return target


def write_one(preset, path, backups=None):
    """Validate, back up, then replace atomically. Returns the backup path."""
    # Serialise and re-parse before touching the filesystem. If the preset dict
    # holds something unserialisable, we find out now rather than half way
    # through replacing a working file.
    try:
        body = json.dumps(preset, ensure_ascii=False, indent=4, sort_keys=True)
        json.loads(body)
    except (TypeError, ValueError) as e:
        raise PresetWriteError("preset is not valid JSON: %s" % e)

    directory = os.path.dirname(path)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as e:
        raise PresetWriteError("cannot create %s: %s" % (directory, e))

    backup = back_up(path, backups)

    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".preset-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise PresetWriteError("cannot write %s: %s" % (path, e))
    return backup


def write_all(preset, targets, backups=None):
    """Write the same preset to every profile directory Orca might read.

    There are two: user\\default\\ and user\\<account id>\\. Which one is read
    depends on whether the user is signed in to an Orca account, and a preset
    written to the wrong one simply never appears in the interface. Writing to
    both is the only reliable answer.

    Returns (written_paths, backup_paths).
    """
    written, backups_made = [], []
    for path in targets:
        backup = write_one(preset, path, backups)
        written.append(path)
        if backup:
            backups_made.append(backup)
    return written, backups_made


def can_write(directory):
    """Is this directory actually writable? Checked before promising anything."""
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".writetest-")
        os.close(fd)
        os.unlink(tmp)
        return True
    except OSError:
        return False
