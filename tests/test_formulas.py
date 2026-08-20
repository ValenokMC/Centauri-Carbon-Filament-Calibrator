# -*- coding: utf-8 -*-
"""The arithmetic, and the scales that give it meaning.

The numbers asserted here are the ones the original tool produced against real
prints. They are not recomputed from the implementation - that would only prove
the code equals itself.
"""
import pytest

from centauri_calibrator import formulas, scales


# ------------------------------------------------------------------ flow

def test_flow_from_wall_thickness():
    # A wall measured 0.445 where 0.42 was asked for: the extruder is giving
    # about 6% too much, so the ratio comes down from 1.0 to 0.944.
    assert formulas.flow(1.0, 0.42, 0.445) == 0.944


def test_flow_scales_with_the_base():
    assert formulas.flow(0.98, 0.42, 0.42) == 0.98


def test_flow_rejects_a_measurement_that_cannot_be_a_wall():
    with pytest.raises(formulas.MeasurementOutOfRange) as e:
        formulas.flow(1.0, 0.42, 12.0)        # measured the whole part
    assert "wall" in str(e.value)


def test_flow_rejects_zero():
    with pytest.raises(formulas.MeasurementOutOfRange):
        formulas.flow(1.0, 0.42, 0)


def test_flow_by_offset_simply_adds():
    assert formulas.flow_by_offset(0.98, 0.02) == 1.0
    assert formulas.flow_by_offset(0.98, -0.05) == 0.93


def test_flow_by_offset_rejects_a_ratio_typed_as_an_offset():
    with pytest.raises(formulas.MeasurementOutOfRange) as e:
        formulas.flow_by_offset(0.98, 0.98)
    assert "tile" in str(e.value)


# ------------------------------------------------------------ shrinkage

def test_shrinkage_is_a_percentage_string():
    assert formulas.shrinkage(100.0, 99.5) == "100.50%"
    assert formulas.shrinkage(100.0, 100.0) == "100.00%"


def test_shrinkage_rejects_an_implausible_result():
    with pytest.raises(formulas.MeasurementOutOfRange) as e:
        formulas.shrinkage(100.0, 90.0)       # 11% - an axis problem, not plastic
    assert "axis" in str(e.value)


# ---------------------------------------------------------------- towers

def test_by_blocks_counts_from_the_bottom():
    # 230 at the bottom, -5 per 10 mm block: 24 mm is inside block 2.
    value, number = formulas.by_blocks(230, -5, 10, 24.0)
    assert (value, number) == (220, 2)


def test_by_blocks_clamps_below_the_first_block():
    value, number = formulas.by_blocks(230, -5, 10, 0.0)
    assert (value, number) == (230, 0)


def test_by_blocks_rejects_a_negative_height():
    with pytest.raises(formulas.MeasurementOutOfRange):
        formulas.by_blocks(230, -5, 10, -1)


def test_continuous_is_linear_below_the_ceiling():
    assert formulas.continuous(5.0, 0.5, 20.0, 25.0) == 15.0


def test_continuous_never_exceeds_the_ceiling():
    """A tower that survived to the top means "at least the cap", not more.
    Without this the PLA tower reported 26 mm3/s where it really ran at 25."""
    assert formulas.continuous(5.0, 0.5, 42.0, 25.0) == 25.0


def test_by_table_picks_the_first_matching_step():
    table = [[1.4, 0.4], [2.2, 0.8], [3.2, 1.2]]
    assert formulas.by_table(table, 1.0) == 0.4
    assert formulas.by_table(table, 1.4) == 0.4
    assert formulas.by_table(table, 1.5) == 0.8
    assert formulas.by_table(table, 99) == 1.2      # above the tower: top step


def test_by_number_is_zero_based():
    assert formulas.by_number(0.0, 0.002, 0) == 0.0
    assert round(formulas.by_number(0.0, 0.002, 10), 4) == 0.02


# ------------------------------------------------------------- rounding

@pytest.mark.parametrize("field,value,expected", [
    ("nozzle_temperature", 219.6, "220"),
    ("nozzle_temperature_initial_layer", 220.0, "220"),
    ("pressure_advance", 0.0250, "0.025"),
    ("pressure_advance", 0.02500001, "0.025"),
    ("filament_flow_ratio", 0.944, "0.944"),
    ("filament_flow_ratio", 1.0, "1.000"),
    ("filament_retraction_length", 0.8, "0.80"),
    ("filament_max_volumetric_speed", 13.456, "13.46"),
    ("filament_shrink", "100.50%", "100.50%"),
])
def test_rounding_matches_what_the_preset_stores(field, value, expected):
    assert formulas.format_field(field, value) == expected


def test_unknown_field_falls_back_to_str():
    assert formulas.format_field("something_new", 5) == "5"


# ------------------------------------------------------------------ scales

def test_every_material_is_present(scales_data):
    assert set(scales_data["materials"]) == {
        "PLA", "PETG", "PETG-CF", "PETG-GF", "ABS", "ASA", "PA", "TPU"}


def test_every_test_declares_what_it_needs(scales_data):
    for material, entry in scales_data["materials"].items():
        for test in entry["tests"]:
            assert test["key"], material
            assert test["input"], material
            assert test["fields"], material
            assert test["question"], material
            assert isinstance(test["order"], int), material


def test_tests_come_back_in_running_order(scales_data):
    """Flow is measured at the final temperature, PA at the final flow, max
    flow at the final PA. Order is correctness, not presentation."""
    for material in scales_data["materials"]:
        orders = [t["order"] for t in scales.tests_for(scales_data, material)]
        assert orders == sorted(orders), material


def test_scales_file_has_no_russian_structural_keys(scales_data):
    """The port to English keys must be complete: a leftover Russian key would
    silently make a test unreadable rather than fail loudly."""
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key.isascii(), key
                if key not in ("question", "hint", "steps", "after",
                               "print_via", "comment", "comment_ru"):
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(scales_data)


def test_template_placeholders_use_the_english_name(scales_data):
    for entry in scales_data["materials"].values():
        for test in entry["tests"]:
            if test.get("file"):
                assert "{material}" in test["file"]
                assert test["file"].endswith(".3mf")


def test_compute_turns_a_temperature_reading_into_two_fields(scales_data):
    tests = scales.tests_for(scales_data, "PLA")
    temperature = next(t for t in tests if t["key"] == "temperature")
    fields, why = scales.compute(temperature, 215, {"filament_flow_ratio": "0.98"})
    assert fields == {"nozzle_temperature": 215,
                      "nozzle_temperature_initial_layer": 215}


def test_compute_respects_the_declared_limits(scales_data):
    tests = scales.tests_for(scales_data, "PLA")
    temperature = next(t for t in tests if t["key"] == "temperature")
    with pytest.raises(formulas.MeasurementOutOfRange):
        scales.compute(temperature, 400, {})


def test_compute_all_collects_errors_without_losing_good_values(scales_data):
    tests = scales.tests_for(scales_data, "PLA")
    fields, why, errors = scales.compute_all(
        tests, {"temperature": 215, "shrinkage": 1.0}, {"filament_flow_ratio": "0.98"})
    assert fields["nozzle_temperature"] == 215      # the good one survived
    assert "shrinkage" in errors                    # the bad one was reported
