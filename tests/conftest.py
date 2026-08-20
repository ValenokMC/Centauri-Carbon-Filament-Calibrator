# -*- coding: utf-8 -*-
"""Fixtures: an isolated data dir, and a fake OrcaSlicer profile tree.

No test touches a real OrcaSlicer installation, a real journal, or a real
preset. The data-dir fixture is autouse so that even a test that forgets to
ask is isolated.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from centauri_calibrator import geometry, paths   # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    target = tmp_path / "appdata"
    monkeypatch.setenv("CALIBRATOR_DATA_DIR", str(target))
    yield target


@pytest.fixture(autouse=True)
def never_touch_real_orca(monkeypatch):
    """Hard stop on the two calls that could disturb a real installation."""
    def refuse(*a, **k):
        raise AssertionError("a test tried to control the real OrcaSlicer")

    from centauri_calibrator import orca
    monkeypatch.setattr(orca, "request_close", refuse)
    monkeypatch.setattr(orca, "open_file", refuse)


# ------------------------------------------------------- fake profile tree

SYSTEM_FILAMENTS = {
    "Elegoo/filament/fdm_filament_common.json": {
        "name": "fdm_filament_common", "filament_flow_ratio": ["1"],
        "nozzle_temperature": ["220"],
    },
    "Elegoo/filament/fdm_filament_pla.json": {
        "name": "fdm_filament_pla", "inherits": "fdm_filament_common",
        "filament_flow_ratio": ["0.98"],
    },
    "Elegoo/filament/Generic PLA @Elegoo Centauri.json": {
        "name": "Generic PLA @Elegoo Centauri", "inherits": "fdm_filament_pla",
    },
    "Elegoo/filament/Generic PETG @Elegoo Centauri.json": {
        "name": "Generic PETG @Elegoo Centauri", "inherits": "fdm_filament_common",
        "filament_flow_ratio": ["0.95"],
    },
    # The same profile name under a different vendor, with a different value.
    # This is the trap collect_system_filaments exists to avoid.
    "OrcaFilamentLibrary/filament/fdm_filament_pla.json": {
        "name": "fdm_filament_pla", "filament_flow_ratio": ["1.0"],
    },
}


@pytest.fixture
def fake_orca(tmp_path):
    """A minimal but realistic OrcaSlicer tree, with two account folders."""
    install = tmp_path / "OrcaSlicer"
    profiles = install / "resources" / "profiles"
    for relative, body in SYSTEM_FILAMENTS.items():
        path = profiles / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")
    (profiles / "Elegoo.json").write_text(
        json.dumps({"version": "2.4.2.0", "name": "Elegoo"}), encoding="utf-8")

    appdata = tmp_path / "appdata-roaming"
    user = appdata / "OrcaSlicer" / "user"
    for account in ("default", "884400112233"):
        for kind in ("filament", "process", "machine"):
            (user / account / kind).mkdir(parents=True, exist_ok=True)

    # A user machine preset with a network address - entirely invented.
    (user / "884400112233" / "machine" / "My Centauri.json").write_text(
        json.dumps({
            "name": "My Centauri",
            "inherits": "Elegoo Centauri Carbon 0.4 nozzle",
            "printer_settings_id": "Elegoo Centauri Carbon 0.4 nozzle",
            "print_host": "10.0.0.42",
            "host_type": "elegoolink",
        }), encoding="utf-8")

    return {"install": str(install), "appdata": str(appdata),
            "user_root": str(user)}


@pytest.fixture
def sample_template(tmp_path):
    """A .3mf that looks like a saved Orca project, carrying invented
    personal data so the sanitiser has something to remove."""
    parts, _ = geometry.shrinkage_parts()
    config = {
        "filament_flow_ratio": ["0.98"],
        "filament_settings_id": ["Someones Private PLA"],
        "printer_settings_id": "Someones Printer 0.4",
        "printer_model": "Elegoo Centauri Carbon",
        "nozzle_temperature": ["220"],
        "print_host": "10.0.0.42",
        "host_type": "elegoolink",
        "layer_height": "0.2",
    }
    path = tmp_path / "sample.3mf"
    geometry.write_project(str(path), parts, config, "sample")
    return str(path)


@pytest.fixture
def scales_data():
    from centauri_calibrator import scales
    return scales.load()
