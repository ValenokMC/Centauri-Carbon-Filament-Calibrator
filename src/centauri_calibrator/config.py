# -*- coding: utf-8 -*-
"""What the setup wizard found, saved so the user is not asked twice."""
import json
import os
import tempfile

from . import paths


DEFAULTS = {
    "orca_install_dir": "",
    "orca_version": "",           # legacy: Elegoo profile bundle version
    "orca_app_version": "",
    "profile_bundle_version": "",
    "appdata_root": "",           # empty means "use %APPDATA%"
    "machine_preset": "",         # the user's Centauri Carbon preset name
    "machine_fingerprint": "",
    "firmware_backend": "stock",  # stock SDCP, or COSMOS/Moonraker
    "print_host": "",             # legacy; live-wizard workflow ignores it
    "nozzle": "0.4",
    # Retained for compatibility with early config files.  Permission is now
    # process-local and this value is always normalised to False on load.
    "write_to_orca": False,
}


class ConfigError(Exception):
    pass


def load(path=None):
    p = path or paths.config_path(create=False)
    if not os.path.exists(p):
        raise ConfigError("Настройка не найдена: %s\nЗапусти Setup.cmd." % p)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise ConfigError("Не читается %s: %s" % (p, e))
    if not isinstance(data, dict):
        raise ConfigError("%s не содержит настроек." % p)
    merged = dict(DEFAULTS)
    merged.update(data)
    # v1.0 stored the Elegoo profile bundle in ``orca_version``.  Preserve
    # that meaning when loading an old config; treating it as the application
    # version would make a value such as 02.04.00.06 look like Orca itself.
    if (not merged.get("profile_bundle_version")
            and merged.get("orca_version")):
        merged["profile_bundle_version"] = merged["orca_version"]
    merged["write_to_orca"] = False
    return merged


def load_or_default():
    try:
        return load()
    except ConfigError:
        return dict(DEFAULTS)


def save(cfg, path=None):
    p = path or paths.config_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4, sort_keys=True)
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def summary(cfg):
    """Lines for a human."""
    return [
        "OrcaSlicer      : %s" % (cfg.get("orca_install_dir") or "(не найден)"),
        "Версия Orca     : %s" % (cfg.get("orca_app_version") or "неизвестна"),
        "Пакет Elegoo    : %s" % (cfg.get("profile_bundle_version") or "неизвестен"),
        "Прошивка        : %s" % cfg.get("firmware_backend", "stock"),
        "Профиль принтера: %s" % (cfg.get("machine_preset") or "(не выбран)"),
        "Сопло           : %s мм" % cfg.get("nozzle", "0.4"),
        "Запись в Orca   : только после подтверждения в каждом запуске",
    ]
