# -*- coding: utf-8 -*-
"""The parts where a bug means damaged data, not a wrong number.

Name handling, preset writing, and the promise that a template is never
modified. Each of these guards something the user cannot easily undo.
"""
import hashlib
import json
import os
import re

import pytest

from centauri_calibrator import (config as config_mod, geometry, journal, names,
                                 orca, paths, plates, presets, session, templates)


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ------------------------------------------------------------ name safety

@pytest.mark.parametrize("raw", [
    "../escape", "..\\escape", "a/b", "a\\b", "C:\\Windows\\system32",
    "~/secrets", "..", "../../etc/passwd", "spool:stream",
])
def test_path_like_names_are_refused(raw):
    with pytest.raises(names.UnsafeName):
        names.safe_name(raw)


@pytest.mark.parametrize("raw", ["", "   ", None, "..", "   .  "])
def test_empty_names_are_refused(raw):
    with pytest.raises(names.UnsafeName):
        names.safe_name(raw)


@pytest.mark.parametrize("raw", ["CON", "con", "PRN", "nul", "COM1", "LPT9",
                                 "CON.json", "aux.txt"])
def test_windows_device_names_are_defused(raw):
    """CON, con.txt and CoN.json all open the console, not a file."""
    safe = names.safe_name(raw)
    assert safe.split(".")[0].upper() not in names.WINDOWS_RESERVED


@pytest.mark.parametrize("raw,expected", [
    ("eSUN PLA+ Matte", "eSUN PLA+ Matte"),
    ("Generic PETG-CF", "Generic PETG-CF"),
    ("ELEGOO PLA (blue)", "ELEGOO PLA (blue)"),
    ("spool   with   spaces", "spool with spaces"),
    ("trailing dot.", "trailing dot"),
    ("trailing space   ", "trailing space"),
])
def test_ordinary_names_survive_intact(raw, expected):
    assert names.safe_name(raw) == expected


def test_control_characters_are_replaced():
    assert "\n" not in names.safe_name("line\nbreak")
    assert "\x00" not in names.safe_name("null\x00byte")


def test_names_are_length_capped():
    assert len(names.safe_name("x" * 500)) <= names.MAX_LENGTH


def test_cyrillic_names_are_allowed():
    """The interface is Russian; a Russian spool name has to work."""
    assert names.safe_name("НИТ PLA Синий") == "НИТ PLA Синий"


def test_safe_join_stays_inside_the_data_directory(tmp_path):
    base = str(tmp_path)
    assert names.safe_join(base, "ok").startswith(os.path.abspath(base))
    with pytest.raises(names.UnsafeName):
        names.safe_join(base, "../outside")


def test_vendor_is_read_off_the_front_of_the_name():
    vendors = ["ELEGOO", "eSUN", "SUNLU"]
    assert names.vendor_of("eSUN PLA Matte", vendors) == "eSUN"
    assert names.vendor_of("Unknown Brand PLA", vendors) == "Unknown"


# --------------------------------------------------------- preset writing

@pytest.fixture
def preset_body():
    return presets.build("Demo PLA", "Generic PLA @Elegoo Centauri",
                         {"nozzle_temperature": 215, "filament_flow_ratio": 0.98},
                         compatible_printers=["Elegoo Centauri Carbon 0.4 nozzle"],
                         vendor="ExampleBrand")


def test_preset_is_an_overlay_not_a_full_profile(preset_body):
    """Only measured fields, so an Elegoo profile update does not wipe the
    calibration and the diff a user sees is readable."""
    assert preset_body["inherits"] == "Generic PLA @Elegoo Centauri"
    measured = [k for k in preset_body if k.startswith(("nozzle_", "filament_"))
                and k != "filament_settings_id" and k != "filament_vendor"]
    assert set(measured) == {"nozzle_temperature", "filament_flow_ratio"}


def test_pressure_advance_enables_its_own_switch():
    preset = presets.build("D", "B", {"pressure_advance": 0.025},
                           compatible_printers=["P"])
    assert preset["enable_pressure_advance"] == ["1"]


def test_plan_reports_create_versus_replace(tmp_path, preset_body):
    existing = tmp_path / "Demo PLA.json"
    existing.write_text("{}", encoding="utf-8")
    missing = tmp_path / "Other.json"
    steps = presets.plan(preset_body, [str(existing), str(missing)])
    assert steps == [(str(existing), "replace"), (str(missing), "create")]


def test_existing_preset_is_backed_up_before_replacement(tmp_path, preset_body):
    target = tmp_path / "Demo PLA.json"
    target.write_text(json.dumps({"marker": "original"}), encoding="utf-8")
    before = digest(str(target))

    backup = presets.write_one(preset_body, str(target))

    assert backup and os.path.exists(backup)
    assert digest(backup) == before
    assert json.loads(target.read_text(encoding="utf-8"))["name"] == "Demo PLA"


def test_write_leaves_no_temporary_files(tmp_path, preset_body):
    target = tmp_path / "Demo PLA.json"
    presets.write_one(preset_body, str(target))
    leftovers = [n for n in os.listdir(tmp_path) if n.startswith(".preset-")]
    assert leftovers == []


def test_result_is_always_valid_json(tmp_path, preset_body):
    target = tmp_path / "Demo PLA.json"
    presets.write_one(preset_body, str(target))
    json.loads(target.read_text(encoding="utf-8"))       # raises if broken


def test_unserialisable_preset_is_refused_before_anything_is_touched(tmp_path):
    target = tmp_path / "Demo PLA.json"
    target.write_text(json.dumps({"marker": "original"}), encoding="utf-8")
    before = digest(str(target))

    with pytest.raises(presets.PresetWriteError):
        presets.write_one({"bad": object()}, str(target))

    # The original survived untouched - that is the whole point.
    assert digest(str(target)) == before


def test_write_all_covers_every_account_directory(tmp_path, preset_body):
    targets = [str(tmp_path / "default" / "Demo.json"),
               str(tmp_path / "884400112233" / "Demo.json")]
    written, _ = presets.write_all(preset_body, targets)
    assert len(written) == 2
    for path in targets:
        assert os.path.exists(path)


# ---------------------------------------------------- templates stay pristine

def test_personalising_never_modifies_the_template(sample_template, tmp_path):
    before = digest(sample_template)
    plates.personalise(sample_template, "Demo PLA",
                       {"nozzle_temperature": 215},
                       folder=str(tmp_path / "out"),
                       network={"print_host": "10.0.0.99"})
    assert digest(sample_template) == before


def test_personal_copy_receives_the_values_and_the_host(sample_template, tmp_path):
    copy = plates.personalise(sample_template, "Demo PLA",
                              {"nozzle_temperature": 215},
                              folder=str(tmp_path / "out"),
                              network={"print_host": "10.0.0.99"})
    info = plates.inspect(copy)
    assert info["print_host"] == "10.0.0.99"
    config = plates.read_config(plates.read_entries(copy))
    assert config["nozzle_temperature"] == ["215"]
    assert config["filament_settings_id"] == ["Demo PLA"]


def test_personal_copy_without_a_host_gets_none(sample_template, tmp_path):
    """No print_host configured is a supported setup, not a broken one."""
    source_host = plates.inspect(sample_template)["print_host"]
    assert source_host                                  # the fixture has one
    copy = plates.personalise(sample_template, "Demo PLA", {},
                              folder=str(tmp_path / "out"), network={})
    # It inherits whatever the template had; the template we ship has none.
    assert plates.inspect(copy) is not None


def test_sanitising_removes_every_personal_key(sample_template, tmp_path):
    target = str(tmp_path / "clean.3mf")
    removed = plates.sanitise_template(
        sample_template, target,
        filament_settings_id="Generic PLA @System",
        printer_settings_id="Elegoo Centauri Carbon 0.4 nozzle")

    assert "print_host" in removed
    info = plates.inspect(target)
    assert info["print_host"] is None
    assert info["printer_settings_id"] == "Elegoo Centauri Carbon 0.4 nozzle"
    assert info["filament_settings_id"] == ["Generic PLA @System"]

    body = open(target, "rb").read()
    assert b"10.0.0.42" not in body
    assert b"Someones Private PLA" not in body


def test_bare_geometry_is_not_offered_as_a_personalisable_plate(tmp_path,
                                                                monkeypatch):
    root = tmp_path / "shipped"
    target = root / "PLA" / "2b_shrinkage.3mf"
    parts, _ = geometry.shrinkage_parts()
    geometry.write_model(str(target), parts, "bare")
    monkeypatch.setattr(paths, "templates_dir", lambda: str(root))

    assert templates.resolve("PLA", "2b_shrinkage.3mf") is None


def test_shrinkage_plate_requires_a_local_orca_reference():
    with pytest.raises(plates.PlateError):
        templates.build_shrinkage("PLA")


def test_shrinkage_plate_from_reference_is_safe_and_personalisable(sample_template,
                                                                   tmp_path):
    reference = plates.read_config(plates.read_entries(sample_template))
    target, problems = templates.build_shrinkage("PLA", reference)
    assert problems == []

    info = plates.inspect(target)
    assert plates.CONFIG_ENTRY in info["entries"]
    assert info["print_host"] is None
    assert info["filament_settings_id"] == ["Generic PLA @System"]

    personal = plates.personalise(
        target, "Demo PLA", {"nozzle_temperature": 215},
        folder=str(tmp_path / "personal"),
        network={"print_host": "10.0.0.99"}, machine_preset="My Centauri")
    personal_info = plates.inspect(personal)
    assert personal_info["print_host"] == "10.0.0.99"
    assert personal_info["filament_settings_id"] == ["Demo PLA"]
    assert personal_info["printer_settings_id"] == "My Centauri"


def test_first_preset_write_asks_even_when_internal_call_says_no_repeat(
        tmp_path, monkeypatch):
    cfg = {"write_to_orca": False, "nozzle": "0.4"}
    run = session.Session(cfg, {}, dry_run=False)
    run.material = "PLA"
    run.spool = "Demo PLA"
    run.base = "Generic PLA @Elegoo Centauri"

    target_dir = tmp_path / "orca" / "filament"
    monkeypatch.setattr(orca, "filament_dirs", lambda: [str(target_dir)])
    monkeypatch.setattr(orca, "is_running", lambda: False)
    monkeypatch.setattr(orca, "compatible_printers", lambda nozzle: ["Centauri"])
    monkeypatch.setattr(presets, "preset_version", lambda directories: "2.4.2")
    monkeypatch.setattr(session.support, "maybe_show", lambda **kwargs: False)

    questions = []
    monkeypatch.setattr(session.c, "ask_yes",
                        lambda question, default=True: questions.append(question) or False)
    assert run.save_preset({"nozzle_temperature": 215}, ask=False) is None
    assert questions == ["Записать?"]
    assert not target_dir.exists()
    assert cfg["write_to_orca"] is False

    questions.clear()
    monkeypatch.setattr(session.c, "ask_yes",
                        lambda question, default=True: questions.append(question) or True)
    written = run.save_preset({"nozzle_temperature": 215}, ask=False)
    assert len(written) == 1
    assert questions == ["Записать?"]
    assert cfg["write_to_orca"] is False
    assert run.orca_write_approved is True

    questions.clear()
    run.save_preset({"nozzle_temperature": 220}, ask=False)
    assert questions == []


def test_old_config_permission_cannot_bypass_a_new_run_confirmation(
        tmp_path, monkeypatch):
    cfg = {"write_to_orca": True, "nozzle": "0.4"}
    run = session.Session(cfg, {}, dry_run=False)
    run.material = "PLA"
    run.spool = "Demo PLA"
    run.base = "Generic PLA @Elegoo Centauri"

    target_dir = tmp_path / "orca" / "filament"
    monkeypatch.setattr(orca, "filament_dirs", lambda: [str(target_dir)])
    monkeypatch.setattr(orca, "is_running", lambda: False)
    monkeypatch.setattr(session.c, "ask_yes",
                        lambda question, default=True: False)

    assert run.save_preset({"nozzle_temperature": 215}, ask=False) is None
    assert not target_dir.exists()
    assert run.orca_write_approved is False


def test_old_config_write_permission_is_normalised_to_false(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"write_to_orca": true}', encoding="utf-8")

    assert config_mod.load(str(path))["write_to_orca"] is False


def test_dry_run_creates_no_spool_folder(isolated_data_dir):
    run = session.Session({}, {}, dry_run=True)
    run.spool = "Demo PLA"
    run.load_run()
    assert not isolated_data_dir.exists()


def test_dry_run_validates_template_without_copying_or_opening(sample_template,
                                                               tmp_path,
                                                               monkeypatch):
    run = session.Session({}, {}, dry_run=True)
    run.material = "PLA"
    run.spool = "Demo PLA"
    run.folder = str(tmp_path / "must-not-exist")
    monkeypatch.setattr(templates, "resolve", lambda material, filename: sample_template)
    test = {"file": "{material}/1_temperature.3mf"}

    assert run.prepare_plate(test, {}) == sample_template
    assert not os.path.exists(run.folder)


def test_exit_does_not_claim_a_declined_preset_was_written(monkeypatch):
    run = session.Session({"write_to_orca": False}, {}, dry_run=False)
    run.tests = []
    run.measurements = {}
    monkeypatch.setattr(run, "plate_menu", lambda computed: "__quit__")
    monkeypatch.setattr(run, "save_measurements", lambda: None)
    lines = []
    monkeypatch.setattr(session.c, "say", lines.append)

    assert run._loop() == 0
    assert any("Пресет и журнал не записаны" in line for line in lines)
    assert not any("обновлены после каждого" in line for line in lines)


def test_shipped_templates_contain_nothing_personal():
    """The plates in the repository, checked the same way the release is."""
    root = paths.templates_dir()
    found = 0
    for directory, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".3mf"):
                continue
            found += 1
            path = os.path.join(directory, name)
            info = plates.inspect(path)
            assert info["print_host"] is None, path
            body = open(path, "rb").read()
            for marker in (b"print_host", b"C:\\Users", b"192.168"):
                assert marker not in body, (path, marker)
    assert found >= 8, "expected the shrinkage plates to be present"


# ------------------------------------------------------------------ journal

def test_journal_updates_the_run_rather_than_appending(tmp_path):
    import datetime
    path = str(tmp_path / "Journal.csv")
    day = datetime.date(2026, 1, 15)
    for temperature in (210, 215, 220):
        journal.record(journal.build_row(
            "PLA", "Demo PLA", "Generic PLA @Elegoo Centauri",
            {"nozzle_temperature": temperature}, when=day), path=path)

    rows = open(path, encoding="utf-8-sig").read().strip().splitlines()
    assert len(rows) == 2                     # header plus one run
    assert "220" in rows[1]


def test_journal_lists_previous_spools_newest_first(tmp_path):
    import datetime
    path = str(tmp_path / "Journal.csv")
    journal.record(journal.build_row("PLA", "First", "B", {},
                                     when=datetime.date(2026, 1, 1)), path=path)
    journal.record(journal.build_row("PLA", "Second", "B", {},
                                     when=datetime.date(2026, 2, 1)), path=path)
    previous = journal.previous_spools(path)
    assert [spool for _, spool, _ in previous] == ["Second", "First"]


def test_example_journal_holds_only_invented_values():
    """Checked by digest, not by literal.

    Spelling the forbidden value out here would put it back in the repository -
    which is the thing being prevented. The scanner works the same way, for the
    same reason; see tools/check_public_safety.py.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    body = open(os.path.join(here, "examples", "Journal.example.csv"),
                encoding="utf-8-sig").read()

    forbidden = {
        # sha256 of the author's private spool name, lowercased
        "b93d411e1ae56511462a23fd0a46f68d6b52013be20051c486dfe9273ea179e9",
    }
    words = re.findall(r"[A-Za-z0-9_.:@+-]+", body)
    for start in range(len(words)):
        for span in (1, 2, 3):
            phrase = " ".join(words[start:start + span])
            digest = hashlib.sha256(phrase.lower().encode("utf-8")).hexdigest()
            assert digest not in forbidden, (
                "the example journal holds a private value")

    assert "192.168" not in body
    assert "ExampleBrand" in body
