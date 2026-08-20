# -*- coding: utf-8 -*-
"""Finding OrcaSlicer: the installation, the profiles, the user's presets.

Everything here is read-only except for the explicit "close Orca" helper, and
that one never uses force - see ``request_close``.

All roots are parameters with sensible defaults rather than module constants,
so the test suite can point the whole module at a fake profile tree in a
temporary directory and never touch a real installation.
"""
import glob
import json
import os
import subprocess
import time


PROCESS_NAME = "orca-slicer.exe"

DEFAULT_INSTALL_DIRS = [
    r"C:\Program Files\OrcaSlicer",
    r"C:\Program Files (x86)\OrcaSlicer",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "OrcaSlicer"),
]

SYSTEM_PROFILE_SUBDIR = os.path.join("resources", "profiles")

# The printer this project is actually tested against. Claiming more would be
# a lie the user only discovers after a failed print.
SUPPORTED_PRINTER_MODEL = "Elegoo Centauri Carbon"
SUPPORTED_NOZZLE = "0.4"
TESTED_ORCA_VERSION = "2.4.2"


# ------------------------------------------------------------------ install

def find_installation(candidates=None):
    """The OrcaSlicer install directory, or None."""
    for base in (candidates or DEFAULT_INSTALL_DIRS):
        if base and os.path.isdir(os.path.join(base, *SYSTEM_PROFILE_SUBDIR.split(os.sep))):
            return base
    return None


def system_profiles_root(install_dir):
    return os.path.join(install_dir, *SYSTEM_PROFILE_SUBDIR.split(os.sep))


def installed_version(install_dir):
    """Best-effort version string.

    Orca does not ship a machine-readable version file, so this reads the
    vendor bundle it does ship. A missing version is not fatal: it is reported
    as unknown rather than guessed, and the user is told which version the
    project was tested against.
    """
    bundle = os.path.join(system_profiles_root(install_dir), "Elegoo.json")
    try:
        with open(bundle, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("version") or None
    except (OSError, ValueError):
        return None


def user_root(appdata=None):
    r"""%APPDATA%\OrcaSlicer\user - where presets live."""
    base = appdata or os.environ.get("APPDATA", "")
    return os.path.join(base, "OrcaSlicer", "user")


def account_dirs(appdata=None):
    """Every profile directory Orca might read.

    There are two kinds: ``default`` and one per signed-in account id. Which is
    active depends on whether the user is signed in, and there is no way to
    tell from outside - so both are always considered.
    """
    root = user_root(appdata)
    found = sorted(d for d in glob.glob(os.path.join(root, "*"))
                   if os.path.isdir(d))
    return found or [os.path.join(root, "default")]


def filament_dirs(appdata=None):
    dirs = [os.path.join(d, "filament") for d in account_dirs(appdata)]
    existing = [d for d in dirs if os.path.isdir(d)]
    return existing or [os.path.join(user_root(appdata), "default", "filament")]


def process_dirs(appdata=None):
    dirs = [os.path.join(d, "process") for d in account_dirs(appdata)]
    existing = [d for d in dirs if os.path.isdir(d)]
    return existing or [os.path.join(user_root(appdata), "default", "process")]


def machine_dirs(appdata=None):
    dirs = [os.path.join(d, "machine") for d in account_dirs(appdata)]
    existing = [d for d in dirs if os.path.isdir(d)]
    return existing or [os.path.join(user_root(appdata), "default", "machine")]


# ------------------------------------------------------- system profiles

def collect_system_filaments(system_root, vendors=("Elegoo", "OrcaFilamentLibrary")):
    """System filament profiles by name, from the listed vendors only.

    Profile names in Orca's tree are NOT unique: ``fdm_filament_pla`` exists in
    three dozen vendor folders with different values - 0.98, 0.95, 1, 0.92.
    Scanning everything makes it trivial to pick up someone else's: that is how
    the flow ratio for Generic PLA @Elegoo Centauri once resolved to 1.0
    instead of the real 0.98, which would have thrown the flow calibration off
    by 2%.

    Vendor order sets priority: a profile from Elegoo beats a same-named one
    from the shared library, because the printer is Elegoo's.
    """
    by_name = {}
    for vendor in reversed(list(vendors)):        # last in the list is weakest
        root = os.path.join(system_root, vendor)
        for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
            if os.sep + "filament" + os.sep not in path:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    node = json.load(f)
            except (ValueError, OSError):
                continue                          # non-profiles live here too
            if node.get("name"):
                by_name[node["name"]] = node
    return by_name


def inherited_value(profiles, name, key):
    """A field's value following the inherits chain upward."""
    seen = set()
    while name and name not in seen:
        seen.add(name)
        node = profiles.get(name)
        if node is None:
            return None
        if key in node:
            value = node[key]
            return value[0] if isinstance(value, list) and value else value
        name = node.get("inherits")
    return None


# ------------------------------------------------------ user machine presets

def user_machine_presets(appdata=None):
    """Every user machine preset, as (path, node)."""
    out = []
    for directory in machine_dirs(appdata):
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    out.append((path, json.load(f)))
            except (ValueError, OSError):
                continue
    return out


def centauri_machine_presets(appdata=None, nozzle=SUPPORTED_NOZZLE):
    """User presets that inherit the supported Centauri Carbon profile.

    Deduplicated by preset name. OrcaSlicer keeps the same preset in every
    account folder, so a straight scan returns each one twice - which would
    show the user a choice between two identical names and make the wizard
    look broken.
    """
    system_name = "%s %s nozzle" % (SUPPORTED_PRINTER_MODEL, nozzle)
    matches, seen = [], set()
    for path, node in user_machine_presets(appdata):
        name = node.get("name")
        if node.get("inherits") != system_name or not name or name in seen:
            continue
        seen.add(name)
        matches.append((path, node))
    return system_name, matches


def compatible_printers(appdata=None, nozzle=SUPPORTED_NOZZLE):
    """Printer preset names the filament must declare compatibility with.

    Elegoo's system profiles list compatible printers by name and know nothing
    of the user's own presets. Without an explicit list the calibrated filament
    simply does not appear when a user printer preset is selected - and it
    always is, because that is the only place the network address lives.
    """
    system_name, matches = centauri_machine_presets(appdata, nozzle)
    return sorted({system_name} | {node["name"] for _, node in matches})


def find_print_host(appdata=None, nozzle=SUPPORTED_NOZZLE):
    """The printer's address, if the user already configured it in Orca.

    ``print_host`` lives in the machine preset, not in Orca's general settings.
    Returns a dict suitable for merging into a project config, or {} - and {}
    is a normal, supported outcome, not an error: plenty of people slice to a
    USB stick and never configure network sending at all.
    """
    candidates = []
    for _, node in user_machine_presets(appdata):
        if node.get("print_host"):
            candidates.append(node)
    if not candidates:
        return {}

    system_name = "%s %s nozzle" % (SUPPORTED_PRINTER_MODEL, nozzle)
    # There are several presets with an address now - one per nozzle, plus a
    # manual-colour-change variant. Take the one inheriting the supported
    # profile: the plates are made for that nozzle, and substituting a 0.2 here
    # would build a plate that cannot print.
    ours = [n for n in candidates if n.get("inherits") == system_name] or candidates
    # Of those, the plain one: the manual-colour-change preset carries M600 in
    # its G-code, and there is no reason to drag that into a test tower.
    plain = [n for n in ours if n.get("manual_filament_change", "0") != "1"]
    node = (plain or ours)[0]
    return {
        "print_host": node["print_host"],
        "host_type": node.get("host_type", "elegoolink"),
        "printer_settings_id": node.get("printer_settings_id", node["name"]),
    }


# ------------------------------------------------------------- the process

def is_running(process_name=PROCESS_NAME):
    """Is OrcaSlicer open right now?"""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq " + process_name, "/FO", "CSV", "/NH"],
            capture_output=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return process_name.encode() in (out or b"").lower()


def request_close(timeout=25, process_name=PROCESS_NAME, poll=0.5):
    """Ask OrcaSlicer to close, and wait for it to actually go.

    Closing happens BEFORE a preset is written, not after: Orca holds presets
    in memory and may write its own copy back over ours on exit. It also reads
    them only at start-up, so the next plate needs a restart regardless.

    Deliberately without /F. A forced kill discards an unsaved project without
    asking, and a calibration run is hours of the user's time. If Orca is
    sitting on a "save changes?" dialog we would rather time out and ask the
    person to deal with it than throw their work away.

    Returns True only if the process really exited.
    """
    try:
        subprocess.run(["taskkill", "/IM", process_name],
                       capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_running(process_name):
            return True
        time.sleep(poll)
    return False


def open_file(path):
    """Open a project in Orca so the user does not hunt for it in folders."""
    try:
        os.startfile(path)              # noqa: S606 - Windows-only by design
        return True
    except (OSError, AttributeError):
        return False


# ------------------------------------------------------------- diagnosis

def survey(appdata=None, install_candidates=None):
    """Everything the wizard and the doctor command need, in one read-only pass."""
    install = find_installation(install_candidates)
    report = {
        "install_dir": install,
        "version": installed_version(install) if install else None,
        "tested_version": TESTED_ORCA_VERSION,
        "user_root": user_root(appdata),
        "account_dirs": account_dirs(appdata),
        "filament_dirs": filament_dirs(appdata),
        "machine_presets": [],
        "print_host_configured": False,
        "system_profiles": 0,
    }
    if install:
        profiles = collect_system_filaments(system_profiles_root(install))
        report["system_profiles"] = len(profiles)
    _, matches = centauri_machine_presets(appdata)
    report["machine_presets"] = [node.get("name") for _, node in matches]
    report["print_host_configured"] = bool(find_print_host(appdata))
    return report
