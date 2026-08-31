# -*- coding: utf-8 -*-
"""Discovering OrcaSlicer, and the once-a-month support note."""
import json
import os

from centauri_calibrator import __main__ as cli
from centauri_calibrator import orca, support, wizard


# ------------------------------------------------------------- discovery

def test_installation_is_found_by_its_profile_folder(fake_orca):
    found = orca.find_installation([fake_orca["install"], r"C:\nowhere"])
    assert found == fake_orca["install"]


def test_missing_installation_returns_none():
    assert orca.find_installation([r"C:\nowhere", r"C:\also-nowhere"]) is None


def test_version_is_read_from_the_vendor_bundle(fake_orca):
    assert orca.installed_version(fake_orca["install"]) == "2.4.2.0"


def test_unknown_version_is_reported_as_none(tmp_path):
    (tmp_path / "resources" / "profiles").mkdir(parents=True)
    assert orca.installed_version(str(tmp_path)) is None


def test_application_and_profile_bundle_versions_are_separate(fake_orca):
    assert orca.application_version(
        fake_orca["install"],
        registry_entries=[("OrcaSlicer", "2.4.2")]) == "2.4.2"
    assert orca.profile_bundle_version(fake_orca["install"]) == "2.4.2.0"


def test_setup_refuses_cosmos_without_matching_machine_profile(monkeypatch):
    monkeypatch.setattr(orca, "centauri_machine_presets",
                        lambda **kwargs: ("Elegoo Centauri Carbon 0.4 nozzle", []))

    assert wizard.step_machine_preset({}, orca.BACKEND_COSMOS) == (None, "")


def test_both_account_directories_are_found(fake_orca):
    accounts = orca.account_dirs(fake_orca["appdata"])
    names = sorted(os.path.basename(a) for a in accounts)
    assert names == ["884400112233", "default"]


def test_filament_dirs_cover_every_account(fake_orca):
    dirs = orca.filament_dirs(fake_orca["appdata"])
    assert len(dirs) == 2
    assert all(d.endswith("filament") for d in dirs)


def test_missing_user_tree_falls_back_to_default(tmp_path):
    dirs = orca.filament_dirs(str(tmp_path))
    assert len(dirs) == 1
    assert dirs[0].endswith(os.path.join("default", "filament"))


# --------------------------------------------------- the same-name trap

def test_vendor_priority_prevents_picking_the_wrong_profile(fake_orca):
    """fdm_filament_pla exists under two vendors with different flow ratios.
    Elegoo must win, or the flow calibration starts from 1.0 instead of 0.98
    and every result is 2% out."""
    profiles = orca.collect_system_filaments(
        orca.system_profiles_root(fake_orca["install"]))
    assert profiles["fdm_filament_pla"]["filament_flow_ratio"] == ["0.98"]


def test_inherited_value_walks_up_the_chain(fake_orca):
    profiles = orca.collect_system_filaments(
        orca.system_profiles_root(fake_orca["install"]))
    # Generic PLA -> fdm_filament_pla has the ratio.
    assert orca.inherited_value(profiles, "Generic PLA @Elegoo Centauri",
                                "filament_flow_ratio") == "0.98"
    # ...and nozzle_temperature only exists two levels up.
    assert orca.inherited_value(profiles, "Generic PLA @Elegoo Centauri",
                                "nozzle_temperature") == "220"


def test_inherited_value_returns_none_for_an_unknown_field(fake_orca):
    profiles = orca.collect_system_filaments(
        orca.system_profiles_root(fake_orca["install"]))
    assert orca.inherited_value(profiles, "Generic PLA @Elegoo Centauri",
                                "no_such_field") is None


def test_inheritance_loop_does_not_hang():
    profiles = {"a": {"inherits": "b"}, "b": {"inherits": "a"}}
    assert orca.inherited_value(profiles, "a", "x") is None


# ------------------------------------------------------------ print host

def test_print_host_is_found_in_the_user_machine_preset(fake_orca):
    found = orca.find_print_host(fake_orca["appdata"])
    assert found["print_host"] == "10.0.0.42"
    assert found["host_type"] == "elegoolink"


def test_no_print_host_is_an_empty_dict_not_an_error(tmp_path):
    assert orca.find_print_host(str(tmp_path)) == {}


def test_doctor_does_not_create_its_data_directory(isolated_data_dir,
                                                    monkeypatch):
    monkeypatch.setattr(orca, "survey", lambda: {
        "install_dir": r"C:\Fake\OrcaSlicer",
        "version": "2.4.2",
        "tested_version": "2.4.2",
        "system_profiles": 1,
        "account_dirs": [],
        "machine_presets": [],
        "print_host_configured": False,
    })
    assert cli.cmd_doctor() == 0
    assert not isolated_data_dir.exists()


def test_manual_colour_change_preset_is_avoided(fake_orca, tmp_path):
    """That preset carries M600 in its G-code; a test tower does not want it."""
    machine = os.path.join(fake_orca["user_root"], "884400112233", "machine")
    with open(os.path.join(machine, "Manual.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "Manual colour", "print_host": "10.0.0.77",
                   "inherits": "Elegoo Centauri Carbon 0.4 nozzle",
                   "manual_filament_change": "1"}, f)
    found = orca.find_print_host(fake_orca["appdata"])
    assert found["print_host"] == "10.0.0.42"


def _add_cosmos_preset(fake_orca, name="Centauri COSMOS 0.4"):
    machine = os.path.join(fake_orca["user_root"], "884400112233", "machine")
    path = os.path.join(machine, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "name": name,
            "inherits": "Elegoo Centauri Carbon 0.4 nozzle",
            "printer_settings_id": name,
            "print_host": "10.0.0.88",
            "host_type": "moonraker",
            "machine_start_gcode": "PRINT_START",
        }, f)
    return path


def test_cosmos_and_stock_machine_presets_are_separate_contexts(fake_orca):
    _add_cosmos_preset(fake_orca)
    _, cosmos = orca.centauri_machine_presets(
        fake_orca["appdata"], backend=orca.BACKEND_COSMOS)
    _, stock = orca.centauri_machine_presets(
        fake_orca["appdata"], backend=orca.BACKEND_STOCK)
    assert [node["name"] for _, node in cosmos] == ["Centauri COSMOS 0.4"]
    assert "Centauri COSMOS 0.4" not in [node["name"] for _, node in stock]
    assert "My Centauri" in [node["name"] for _, node in stock]


def test_cosmos_filament_compatibility_is_only_the_selected_profile(fake_orca):
    _add_cosmos_preset(fake_orca)
    compatible = orca.compatible_printers(
        fake_orca["appdata"], machine_preset="Centauri COSMOS 0.4",
        backend=orca.BACKEND_COSMOS)
    assert compatible == ["Centauri COSMOS 0.4"]
    assert "Elegoo Centauri Carbon 0.4 nozzle" not in compatible
    assert "My Centauri" not in compatible


def test_print_host_is_taken_from_exact_selected_cosmos_profile(fake_orca):
    _add_cosmos_preset(fake_orca)
    found = orca.find_print_host(
        fake_orca["appdata"], machine_preset="Centauri COSMOS 0.4",
        backend=orca.BACKEND_COSMOS)
    assert found["print_host"] == "10.0.0.88"
    assert found["host_type"] == "moonraker"
    assert orca.find_print_host(
        fake_orca["appdata"], machine_preset="missing",
        backend=orca.BACKEND_COSMOS) == {}


def test_machine_fingerprint_ignores_address_but_not_print_semantics():
    original = {"name": "COSMOS", "print_host": "10.0.0.1",
                "machine_start_gcode": "PRINT_START"}
    moved = dict(original, print_host="10.0.0.2")
    changed = dict(original, machine_start_gcode="OTHER_START")
    assert (orca.machine_profile_fingerprint(original) ==
            orca.machine_profile_fingerprint(moved))
    assert (orca.machine_profile_fingerprint(original) !=
            orca.machine_profile_fingerprint(changed))


def test_compatible_printers_include_the_system_and_the_user_preset(fake_orca):
    printers = orca.compatible_printers(fake_orca["appdata"])
    assert "Elegoo Centauri Carbon 0.4 nozzle" in printers
    assert "My Centauri" in printers


def test_survey_is_read_only_and_complete(fake_orca):
    report = orca.survey(fake_orca["appdata"], [fake_orca["install"]])
    assert report["install_dir"] == fake_orca["install"]
    assert report["system_profiles"] > 0
    assert report["print_host_configured"] is True
    assert "My Centauri" in report["machine_presets"]


# ------------------------------------------------------------ the reminder

DAY = 86400


def test_reminder_is_not_due_before_the_first_month():
    installed = 1_000_000.0
    state = {"installed_at": installed}
    assert support.due(state, now=installed + 29 * DAY) is False
    assert support.due(state, now=installed + 31 * DAY) is True


def test_reminder_is_not_due_without_an_install_date():
    assert support.due({}, now=9_999_999_999) is False


def test_reminder_waits_a_full_interval_after_being_shown():
    installed = 1_000_000.0
    shown = installed + 31 * DAY
    state = {"installed_at": installed, "last_reminder_at": shown}
    assert support.due(state, now=shown + 29 * DAY) is False
    assert support.due(state, now=shown + 31 * DAY) is True


def test_install_date_is_stamped_once():
    first = support.mark_installed(when=1_000_000.0)
    again = support.mark_installed(when=2_000_000.0)
    assert first == again == 1_000_000.0


def test_reminder_state_survives_a_restart():
    """The date is on disk, so restarting the program does not reset it."""
    support.mark_installed(when=1_000_000.0)
    now = 1_000_000.0 + 31 * DAY
    lines = []
    assert support.maybe_show(printer=lines.append, now=now) is True
    # Nothing is cached in memory: a fresh read must still say "not due".
    assert support.due(now=now + DAY) is False


def test_reminder_never_appears_in_a_dry_run():
    """A dry run is a rehearsal. Asking for money for something the user has
    not actually done yet would be worse than not asking at all."""
    support.mark_installed(when=1_000_000.0)
    now = 1_000_000.0 + 31 * DAY
    lines = []
    assert support.maybe_show(printer=lines.append, now=now, dry_run=True) is False
    assert lines == []
    # And the interval was not spent.
    assert support.due(now=now) is True


def test_reminder_text_is_two_lines_at_most():
    assert len(support.REMINDER_TEXT.strip().splitlines()) <= 2


def test_support_links_are_present_and_untracked():
    assert support.TRIBUTE_URL_WEB.startswith("https://")
    for url in (support.TRIBUTE_URL_WEB, support.TRIBUTE_URL_TELEGRAM):
        for marker in ("utm_", "ref=", "click_id"):
            assert marker not in url.lower()


def test_about_screen_lists_every_link():
    text = "\n".join(support.about_lines())
    assert support.GITHUB_URL in text
    assert support.ISSUES_URL in text
    assert support.SUPPORT_BOT_URL in text
    assert support.TRIBUTE_URL_WEB in text


def test_browser_is_never_opened_without_confirmation():
    opened = []
    assert support.open_tribute(confirm=False, opener=opened.append) is False
    assert opened == []
    assert support.open_tribute(confirm=True, opener=opened.append) is True
    assert opened == [support.TRIBUTE_URL_WEB]


def test_machine_presets_are_deduplicated_across_accounts(fake_orca):
    """Orca keeps the same preset in every account folder. Listing it once per
    folder would offer the user a choice between two identical names."""
    import json, os, shutil
    user = fake_orca["user_root"]
    src = os.path.join(user, "884400112233", "machine", "My Centauri.json")
    dst = os.path.join(user, "default", "machine", "My Centauri.json")
    shutil.copy2(src, dst)

    _, matches = orca.centauri_machine_presets(fake_orca["appdata"])
    names = [node["name"] for _, node in matches]
    assert names == ["My Centauri"]
    assert orca.compatible_printers(fake_orca["appdata"]).count("My Centauri") == 1
