# -*- coding: utf-8 -*-
"""Turning raw measurements into preset values.

There is deliberately no input and no file access here - only arithmetic, so a
formula can be corrected without touching the dialog, and checked in one line:

    python -c "from centauri_calibrator import formulas; print(formulas.flow(1.0, 0.42, 0.445))"

Each function takes a raw measurement (millimetres off a caliper, the height of
a block on a tower) and returns the value that goes into the preset.

The bounds are not decoration. A caliper reading off by a factor of ten, or a
measurement taken on the wrong face, produces a plausible-looking number that
would quietly ruin every print made with the resulting preset. Refusing it and
saying which mistake is likely is the whole point.
"""
import math


class MeasurementOutOfRange(ValueError):
    """The measurement does not fit the test's scale - nearly always a typo."""


def flow(base_flow, target_width, measured_width):
    """Flow ratio from the thickness of a single wall.

    A cube is printed one wall thick at a known line width, measured with a
    caliper in four places and averaged. A wall thicker than asked for means
    the extruder is delivering too much, so the flow is cut proportionally.
    """
    if measured_width <= 0:
        raise MeasurementOutOfRange("wall thickness must be greater than zero")
    value = base_flow * (target_width / measured_width)
    if not 0.7 <= value <= 1.3:
        raise MeasurementOutOfRange(
            "flow came out at {:.3f}, which is far outside anything sensible. "
            "Check that you measured the wall and not the whole part, and that "
            "the line width really was {} mm".format(value, target_width))
    return round(value, 3)


def flow_by_offset(base_flow, offset):
    """Flow ratio from Orca's own test (YOLO / LinearFlow).

    The tiles are labelled with a direct addition to the ratio, not a
    percentage: Orca prints each tile at print_flow_ratio = (base + offset) /
    base, so the totals simply add. The method is visual - you pick the tile
    with the flattest top surface - and it is steadier than measuring a thin
    wall with a caliper, where jaw pressure alone can shift the answer by 5%.

    The offset arrives as a list, because a repeat run is printed with the
    corrected ratio already in place: its tiles are labelled relative to that,
    not to the base. So 0.98 + 0.02 + 0 is 1.000, not 0.98 - an honest zero on
    the second plate means "this one is right", and adding it to the base
    instead would quietly undo the first run. A bare number is still accepted;
    that is how runs recorded before this change are stored.
    """
    offsets = list(offset) if isinstance(offset, (list, tuple)) else [offset]
    value = base_flow + sum(float(item) for item in offsets)
    if not 0.7 <= value <= 1.3:
        raise MeasurementOutOfRange(
            "flow came out at {:.3f}, which is far outside anything sensible. "
            "Check that you are entering the tile's label (-0.05 to 0.05) and "
            "not the ratio itself".format(value))
    return round(value, 3)


def shrinkage(nominal, measured):
    """Shrinkage as the percentage the filament_shrink field expects.

    100% means the part came out exactly at nominal. Above 100% means the
    plastic shrank and the slicer compensates by inflating the model.
    """
    if measured <= 0:
        raise MeasurementOutOfRange("the measurement must be greater than zero")
    percent = nominal / measured * 100
    if not 97 <= percent <= 103:
        raise MeasurementOutOfRange(
            "shrinkage came out at {:.2f}%, which looks more like a missed axis "
            "calibration or the wrong face measured than a property of the "
            "plastic".format(percent))
    return "{:.2f}%".format(percent)


def by_blocks(start, step, block_height, measured_height, first_layer_height=0.0):
    """A value from a tower built in steps: temperature, retraction.

    The bottom block prints at ``start`` and each one above shifts by ``step``.
    Measure the height at which the part looks best and work out which block
    that is. ``step`` may be negative - temperature towers are usually cooler
    towards the top.

    Returns (value, block_number).
    """
    if measured_height < 0:
        raise MeasurementOutOfRange("height cannot be negative")
    if block_height <= 0:
        raise MeasurementOutOfRange("block height must be greater than zero")
    number = math.floor((measured_height - first_layer_height) / block_height)
    if number < 0:
        number = 0
    return start + number * step, number


def continuous(start, step_per_mm, measured_height, ceiling=None):
    """A value from a tower where the parameter rises smoothly, without steps.

    This is how the maximum volumetric flow test works: measure the height at
    which under-extrusion appears and take the rate just below it.

    ``ceiling`` is the cap on the ramp. Above the height where the ramp hits the
    cap the tower prints at the cap, and a linear formula would overstate the
    result there: for PLA at 42 mm it gave 26 mm3/s when the last two
    millimetres actually ran at 25. If the tower survived to the top, the honest
    answer is "at least the cap", not an invented number above it.
    """
    if measured_height < 0:
        raise MeasurementOutOfRange("height cannot be negative")
    value = start + measured_height * step_per_mm
    return min(value, ceiling) if ceiling else value


def by_table(table, measured_height):
    """A value from a "height up to -> value" table.

    Needed where the steps are uneven and no formula describes them. The
    retraction tower from Orca's wizard is exactly that: the bottom block is
    1.4 mm, the next 0.8, then one millimetre each. The table is taken from the
    Calib_Retraction_tower markers in the wizard's own G-code and checked
    against the actual retractions.
    """
    if measured_height < 0:
        raise MeasurementOutOfRange("height cannot be negative")
    for boundary, value in table:
        if measured_height <= boundary:
            return value
    return table[-1][1]          # above the tower: the top step


def by_number(start, step, number):
    """A value from a flat test whose variants are numbered: the PA pattern.

    The number is zero-based, as printed on the part.
    """
    if number < 0:
        raise MeasurementOutOfRange("a line number cannot be negative")
    return start + number * step


# How each preset field is rounded: thousandths matter in PA, temperature has
# no fractions at all, and the slicer will silently swallow whatever nonsense
# it is given.
ROUNDING = {
    "nozzle_temperature": lambda v: str(int(round(v))),
    "nozzle_temperature_initial_layer": lambda v: str(int(round(v))),
    "pressure_advance": lambda v: "{:.4f}".format(v).rstrip("0").rstrip("."),
    "filament_flow_ratio": lambda v: "{:.3f}".format(v),
    "filament_retraction_length": lambda v: "{:.2f}".format(v),
    "filament_max_volumetric_speed": lambda v: "{:.2f}".format(v),
    "filament_shrink": lambda v: v if isinstance(v, str) else "{:.2f}%".format(v),
}


def format_field(field, value):
    """Render a number the way the preset stores it.

    A string passes through untouched: that is how a value pinned by hand in
    the slicer arrives - already in the preset's own form, with nothing left to
    round, and every rounding function above expects a number.
    """
    if isinstance(value, str):
        return value
    return ROUNDING.get(field, str)(value)
