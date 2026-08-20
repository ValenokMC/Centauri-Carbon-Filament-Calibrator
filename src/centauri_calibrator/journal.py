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


HEADER = ["date", "material", "spool", "base", "temperature", "flow",
          "pressure_advance", "max_flow", "retraction", "shrinkage", "note"]

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
    seen, out = set(), []
    for row in reversed(rows[1:]):
        if len(row) >= 3 and (row[1], row[2]) not in seen:
            seen.add((row[1], row[2]))
            out.append((row[1], row[2], row[0]))
    return out


def build_row(material, spool, base, fields, when=None, note=""):
    day = (when or datetime.date.today()).isoformat()
    return [day, material, spool, base] + [
        formulas.format_field(k, fields[k]) if k in fields else ""
        for k in FIELD_ORDER] + [note]


def record(row, path=None):
    """Update this run's row rather than appending a new one.

    The preset is rebuilt after every single measurement, so plain appending
    would grow the journal by six rows per spool instead of one. The row key is
    date plus spool name: one run, one row.
    """
    p = path or paths.journal_path()
    rows = _read_rows(p)
    if not rows or rows[0] != HEADER:
        rows = [HEADER] + rows

    key = (row[0], row[2])
    for index, existing in enumerate(rows[1:], start=1):
        if len(existing) > 2 and (existing[0], existing[2]) == key:
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
