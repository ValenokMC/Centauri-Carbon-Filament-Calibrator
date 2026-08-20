# -*- coding: utf-8 -*-
"""Loading the test scales and turning a measurement into preset fields.

The scales file says what to print, within which limits, and how a raw
measurement becomes a value. Without those numbers a measurement is
meaningless: "12.4 mm" on its own says nothing.
"""
import json
import os

from . import formulas


SCALES_FILE = "scales.json"


class ScalesError(Exception):
    pass


def load(path=None):
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), SCALES_FILE)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise ScalesError("cannot read %s: %s" % (p, e))
    if "materials" not in data:
        raise ScalesError("%s has no materials" % p)
    return data


def materials(data):
    return data["materials"]


def tests_for(data, material):
    """Tests in the order they must be run.

    The order is not arbitrary: flow is measured at the final temperature, PA
    at the final flow, and max flow at the final PA. Running them out of order
    produces numbers that describe a filament nobody has.
    """
    try:
        entry = data["materials"][material]
    except KeyError:
        raise ScalesError("unknown material: %s" % material)
    return sorted(entry["tests"], key=lambda t: t["order"])


def compute(test, measurement, base_values):
    """A measurement -> {field: value}, plus a human explanation.

    Raises formulas.MeasurementOutOfRange when the number cannot be right.
    """
    params = test.get("params") or {}
    kind = test["input"]

    if kind == "direct":
        value, why = measurement, "взято как есть"

    elif kind == "offset":
        base_flow = float(base_values.get("filament_flow_ratio") or 1.0)
        value = formulas.flow_by_offset(base_flow, measurement)
        why = "{} + {:g}".format(base_flow, measurement)

    elif kind == "wall_width":
        base_flow = float(base_values.get("filament_flow_ratio") or 1.0)
        value = formulas.flow(base_flow, params["target_width"], measurement)
        why = "{} x ({} / {})".format(base_flow, params["target_width"], measurement)

    elif kind == "size":
        value = formulas.shrinkage(params["nominal"], measurement)
        why = "{} / {}".format(params["nominal"], measurement)

    elif kind == "table":
        value = formulas.by_table(params["table"], measurement)
        why = "по таблице башни мастера"

    elif kind == "blocks":
        value, number = formulas.by_blocks(
            params["start"], params["step"], params["block_height"], measurement)
        why = "блок №{} снизу".format(number)

    elif kind == "continuous":
        ceiling = params.get("ceiling") or (params["start"] + params["step_per_mm"] * 40)
        raw = formulas.continuous(params["start"], params["step_per_mm"],
                                  measurement, ceiling)
        margin = params.get("margin", 1.0)
        value = raw * margin
        why = "{:.1f} мм³/с срыв, минус запас {:.0%}".format(raw, 1 - margin)

    elif kind == "number":
        value = formulas.by_number(params["start"], params["step"], int(measurement))
        why = "линия №{}".format(int(measurement))

    else:
        raise ScalesError("unknown input kind: %s" % kind)

    if isinstance(value, (int, float)):
        low, high = test.get("limits", [float("-inf"), float("inf")])
        if not low <= value <= high:
            raise formulas.MeasurementOutOfRange(
                "вышло {:.3f}, а осмысленный диапазон {}…{}. "
                "Проверь замер и шкалу теста.".format(value, low, high))

    return {field: value for field in test["fields"]}, why


def compute_all(tests, measurements, base_values):
    """Recompute every entered measurement at once."""
    fields, why, errors = {}, {}, {}
    for test in tests:
        key = test["key"]
        if key not in measurements:
            continue
        try:
            new, explanation = compute(test, measurements[key], base_values)
        except formulas.MeasurementOutOfRange as e:
            errors[key] = str(e)
            continue
        fields.update(new)
        why[key] = explanation
    return fields, why, errors
