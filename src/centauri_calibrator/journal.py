# -*- coding: utf-8 -*-
"""Journal.csv - one row per calibration run.

Lives in the user's data directory and is never published. The repository
carries examples/Journal.example.csv instead, filled with invented values.
"""
import csv
import datetime
import os
import tempfile

from . import formulas, paths


LEGACY_HEADER = ["date", "material", "spool", "base", "temperature", "flow",
                 "pressure_advance", "max_flow", "retraction", "shrinkage", "note"]
CONTEXT_COLUMNS = ["run_id", "firmware_backend", "nozzle", "machine_preset",
                   "machine_fingerprint", "orca_app_version",
                   "profile_bundle_version"]
HEADER = LEGACY_HEADER + CONTEXT_COLUMNS

# The preset fields that go into the columns, in column order.
FIELD_ORDER = ("nozzle_temperature", "filament_flow_ratio", "pressure_advance",
               "filament_max_volumetric_speed", "filament_retraction_length",
               "filament_shrink")

DELIMITER = ";"
# utf-8-sig: Excel opens a plain UTF-8 CSV as mojibake, and this journal is
# meant to be opened in a spreadsheet.
ENCODING = "utf-8-sig"


def _read_rows(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding=ENCODING, newline="") as f:
            return [row for row in csv.reader(f, delimiter=DELIMITER) if row]
    except OSError:
        return []


def previous_spools(path=None):
    """Spools calibrated before, newest first: [(material, spool, date), ...]."""
    rows = _read_rows(path or paths.journal_path(create=False))
    if not rows:
        return []
    header = rows[0]
    try:
        date_i, material_i, spool_i = (
            header.index("date"), header.index("material"), header.index("spool"))
    except ValueError:
        return []
    seen, out = set(), []
    for row in reversed(rows[1:]):
        if len(row) > max(date_i, material_i, spool_i):
            pair = (row[material_i], row[spool_i])
            if pair in seen:
                continue
            seen.add(pair)
            out.append((pair[0], pair[1], row[date_i]))
    return out


def build_row(material, spool, base, fields, when=None, note="", context=None,
              run_id=""):
    day = (when or datetime.date.today()).isoformat()
    row = [day, material, spool, base] + [
        formulas.format_field(k, fields[k]) if k in fields else ""
        for k in FIELD_ORDER] + [note]
    context = context or {}
    row += [str(run_id or "")]
    row += [str(context.get(key) or "") for key in CONTEXT_COLUMNS[1:]]
    return row


def _upgrade_rows(rows):
    if not rows:
        return [HEADER]
    old_header = rows[0]
    if old_header == HEADER:
        return rows
    if old_header != LEGACY_HEADER:
        raise ValueError("unknown Journal.csv header; refusing to replace it")
    upgraded = [HEADER]
    for old in rows[1:]:
        values = {name: old[index] for index, name in enumerate(old_header)
                  if index < len(old)}
        upgraded.append([values.get(name, "") for name in HEADER])
    return upgraded


def _row_key(row):
    run_id = row[HEADER.index("run_id")] if len(row) > HEADER.index("run_id") else ""
    if run_id:
        return ("run", run_id)
    return ("legacy", row[HEADER.index("date")], row[HEADER.index("spool")],
            row[HEADER.index("base")])


def record(row, path=None):
    """Update this run's row rather than appending a new one.

    The preset is rebuilt after every single measurement, so plain appending
    would grow the journal by six rows per spool instead of one. New rows use a
    stable run id; legacy rows use date, spool and base. One run, one row.
    """
    p = path or paths.journal_path()
    rows = _upgrade_rows(_read_rows(p))

    if len(row) != len(HEADER):
        raise ValueError("journal row has %d columns, expected %d" %
                         (len(row), len(HEADER)))
    key = _row_key(row)
    for index, existing in enumerate(rows[1:], start=1):
        if len(existing) == len(HEADER) and _row_key(existing) == key:
            rows[index] = row
            break
    else:
        rows.append(row)

    _write_atomic(p, rows)
    return p


def _write_atomic(path, rows):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".journal-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=ENCODING, newline="") as f:
            csv.writer(f, delimiter=DELIMITER).writerows(rows)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
