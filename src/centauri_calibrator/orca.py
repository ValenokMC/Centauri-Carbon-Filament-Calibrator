# -*- coding: utf-8 -*-
"""Finding OrcaSlicer: the installation, the profiles, the user's presets.

Everything here is read-only except for the explicit "close Orca" helper, and
that one never uses force - see ``request_close``.

All roots are parameters with sensible defaults rather than module constants,
so the test suite can point the whole module at a fake profile tree in a
temporary directory and never touch a real installation.
"""
import glob
import hashlib
import json
import os
import re
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

BACKEND_STOCK = "stock"
BACKEND_COSMOS = "cosmos"
BACKENDS = (BACKEND_STOCK, BACKEND_COSMOS)


# ------------------------------------------------------------------ install

def find_installation(candidates=None):
    """The OrcaSlicer install directory, or None."""
    for base in (candidates or DEFAULT_INSTALL_DIRS):
        if base and os.path.isdir(os.path.join(base, *SYSTEM_PROFILE_SUBDIR.split(os.sep))):
            return base
    return None


def system_profiles_root(install_dir):
    return os.path.join(install_dir, *SYSTEM_PROFILE_SUBDIR.split(os.sep))


def profile_bundle_version(install_dir):
    """Version of Orca's Elegoo profile bundle, not the application."""
    bundle = os.path.join(system_profiles_root(install_dir), "Elegoo.json")
    try:
        with open(bundle, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("version") or None
    except (OSError, ValueError):
        return None


def _registry_versions():
    """Yield (display name, version) from Windows uninstall metadata."""
    try:
        import winreg
    except ImportError:
        return []
    found = []
    roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    base = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    views = [0]
    for flag_name in ("KEY_WOW64_32KEY", "KEY_WOW64_64KEY"):
        flag = getattr(winreg, flag_name, 0)
        if flag not in views:
            views.append(flag)
    for root in roots:
        for view in views:
            try:
                parent = winreg.OpenKey(root, base, 0, winreg.KEY_READ | view)
            except OSError:
                continue
            try:
                count = winreg.QueryInfoKey(parent)[0]
                for index in range(count):
                    try:
                        child_name = winreg.EnumKey(parent, index)
                        with winreg.OpenKey(parent, child_name) as child:
                            name = winreg.QueryValueEx(child, "DisplayName")[0]
                            version = winreg.QueryValueEx(child, "DisplayVersion")[0]
                        found.append((str(name), str(version)))
                    except OSError:
                        continue
            finally:
                winreg.CloseKey(parent)
    return found


def application_version(install_dir=None, registry_entries=None):
    """Best-effort OrcaSlicer application version from uninstall metadata."""
    entries = _registry_versions() if registry_entries is None else registry_entries
    for name, version in entries:
        if str(name).strip().lower() == "orcaslicer" and str(version).strip():
            return str(version).strip()
    return None


def installed_version(install_dir):
    """Compatibility alias for the historically reported bundle version."""
    return profile_bundle_version(install_dir)


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


def machine_profile_fingerprint(node):
    """Stable identity excluding the network address and other personal data."""
    public = {key: value for key, value in (node or {}).items()
              if key not in {"print_host", "print_host_webui", "printhost_apikey"}}
    body = json.dumps(public, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _machine_map(presets):
    return {node.get("name"): node for _, node in presets if node.get("name")}


def inherited_machine_value(node, key, profiles):
    """Read a user-machine field through user-preset inheritance."""
    seen = set()
    current = node
    while isinstance(current, dict):
        name = current.get("name")
        if name in seen:
            return None
        if name:
            seen.add(name)
        if key in current and current[key] not in (None, ""):
            value = current[key]
            return value[0] if isinstance(value, list) and value else value
        current = profiles.get(current.get("inherits"))
    return None


def machine_nozzle(node, profiles=None):
    profiles = profiles or {}
    value = inherited_machine_value(node, "nozzle_diameter", profiles)
    if value not in (None, ""):
        try:
            return ("%g" % float(value))
        except (TypeError, ValueError):
            pass
    text = " ".join(str((node or {}).get(key) or "")
                    for key in ("name", "inherits", "printer_settings_id"))
    match = re.search(r"(?<!\d)(0\.\d+)\s*(?:mm|nozzle)?", text, re.I)
    return match.group(1) if match else ""


def machine_backend(node, profiles=None):
    profiles = profiles or {}
    host_type = str(inherited_machine_value(node, "host_type", profiles) or "").lower()
    text = " ".join(str((node or {}).get(key) or "")
                    for key in ("name", "inherits", "printer_settings_id")).lower()
    if host_type == "moonraker" or "cosmos" in text or "opencentauri" in text:
        return BACKEND_COSMOS
    if host_type in ("elegoolink", "elegoo"):
        return BACKEND_STOCK
    return "unknown"


def machine_context(node, presets=None):
    profiles = _machine_map(presets or [])
    return {
        "machine_preset": (node or {}).get("name", ""),
        "machine_fingerprint": machine_profile_fingerprint(node or {}),
        "firmware_backend": machine_backend(node or {}, profiles),
        "nozzle": machine_nozzle(node or {}, profiles),
        "host_type": str(inherited_machine_value(node or {}, "host_type", profiles) or ""),
    }


def centauri_machine_presets(appdata=None, nozzle=SUPPORTED_NOZZLE, backend=None):
    """User presets that inherit the supported Centauri Carbon profile.

    Deduplicated by preset name. OrcaSlicer keeps the same preset in every
    account folder, so a straight scan returns each one twice - which would
    show the user a choice between two identical names and make the wizard
    look broken.
    """
    system_name = "%s %s nozzle" % (SUPPORTED_PRINTER_MODEL, nozzle)
    presets = user_machine_presets(appdata)
    profiles = _machine_map(presets)
    matches, seen = [], set()
    for path, node in presets:
        name = node.get("name")
        parent = node.get("inherits")
        ancestry = set()
        while parent and parent not in ancestry:
            ancestry.add(parent)
            parent = (profiles.get(parent) or {}).get("inherits")
        detected = machine_backend(node, profiles)
        backend_ok = (not backend or detected == backend or
                      (backend == BACKEND_STOCK and detected == "unknown"))
        if (system_name not in ancestry or not backend_ok or
                not name or name in seen):
            continue
        seen.add(name)
        matches.append((path, node))
    return system_name, matches


def compatible_printers(appdata=None, nozzle=SUPPORTED_NOZZLE,
                        machine_preset=None, backend=None):
    """Printer preset names the filament must declare compatibility with.

    Elegoo's system profiles list compatible printers by name and know nothing
    of the user's own presets. Without an explicit list the calibrated filament
    simply does not appear when a user printer preset is selected - and it
    always is, because that is the only place the network address lives.
    """
    system_name, matches = centauri_machine_presets(appdata, nozzle, backend)
    names = {node["name"] for _, node in matches}
    if machine_preset:
        if backend == BACKEND_COSMOS and machine_preset == system_name:
            return []
        return [machine_preset] if machine_preset in names or machine_preset == system_name else []
    if backend is None:
        names.add(system_name)
    return sorted(names or {system_name})


def find_print_host(appdata=None, nozzle=SUPPORTED_NOZZLE,
                    machine_preset=None, backend=None):
    """The printer's address, if the user already configured it in Orca.

    ``print_host`` lives in the machine preset, not in Orca's general settings.
    Returns a dict suitable for merging into a project config, or {} - and {}
    is a normal, supported outcome, not an error: plenty of people slice to a
    USB stick and never configure network sending at all.
    """
    presets = user_machine_presets(appdata)
    profiles = _machine_map(presets)
    candidates = []
    for _, node in presets:
        host = inherited_machine_value(node, "print_host", profiles)
        if host:
            candidates.append((node, host))
    if not candidates:
        return {}

    # There are several presets with an address now - one per nozzle, plus a
    # manual-colour-change variant. Take the one inheriting the supported
    # profile: the plates are made for that nozzle, and substituting a 0.2 here
    # would build a plate that cannot print.
    ours = [(n, host) for n, host in candidates
            if machine_nozzle(n, profiles) == str(nozzle)
            and (not backend or machine_backend(n, profiles) == backend or
                 (backend == BACKEND_STOCK and machine_backend(n, profiles) == "unknown"))]
    if machine_preset:
        ours = [(n, host) for n, host in ours if n.get("name") == machine_preset]
    if not ours:
        return {}
    # Of those, the plain one: the manual-colour-change preset carries M600 in
    # its G-code, and there is no reason to drag that into a test tower.
    unique = {}
    for node, host in ours:
        unique[(node.get("name"), host, machine_backend(node, profiles))] = (node, host)
    ours = list(unique.values())
    plain = [(n, host) for n, host in ours
             if inherited_machine_value(n, "manual_filament_change", profiles) != "1"]
    choices = plain or ours
    if not machine_preset and len(choices) != 1:
        return {}
    node, host = choices[0]
    return {
        "print_host": host,
        "host_type": inherited_machine_value(node, "host_type", profiles) or "elegoolink",
        "printer_settings_id": node.get("printer_settings_id", node["name"]),
        "machine_preset": node["name"],
        "firmware_backend": machine_backend(node, profiles),
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
        "version": application_version(install) if install else None,
        "profile_bundle_version": profile_bundle_version(install) if install else None,
        "tested_version": TESTED_ORCA_VERSION,
        "user_root": user_root(appdata),
        "account_dirs": account_dirs(appdata),
        "filament_dirs": filament_dirs(appdata),
        "machine_presets": [],
        "machine_contexts": [],
        "print_host_configured": False,
        "system_profiles": 0,
    }
    if install:
        profiles = collect_system_filaments(system_profiles_root(install))
        report["system_profiles"] = len(profiles)
    _, matches = centauri_machine_presets(appdata)
    report["machine_presets"] = [node.get("name") for _, node in matches]
    presets = user_machine_presets(appdata)
    report["machine_contexts"] = [machine_context(node, presets)
                                  for _, node in matches]
    report["print_host_configured"] = bool(find_print_host(appdata))
    return report
