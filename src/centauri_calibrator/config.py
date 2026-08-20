# -*- coding: utf-8 -*-
"""What the setup wizard found, saved so the user is not asked twice."""
import json
import os
import tempfile

from . import paths


DEFAULTS = {
    "orca_install_dir": "",
    "orca_version": "",
    "appdata_root": "",           # empty means "use %APPDATA%"
    "machine_preset": "",         # the user's Centauri Carbon preset name
    "print_host": "",             # optional; empty is a supported setup
    "nozzle": "0.4",
    # Retained for compatibility with early config files.  Permission is now
    # process-local and this value is always normalised to False on load.
    "write_to_orca": False,
    "templates_ready": False,
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
    """Lines for a human. The print host is shown because the user typed it,
    but it is theirs and never leaves this machine."""
    return [
        "OrcaSlicer      : %s" % (cfg.get("orca_install_dir") or "(не найден)"),
        "Версия Orca     : %s" % (cfg.get("orca_version") or "неизвестна"),
        "Профиль принтера: %s" % (cfg.get("machine_preset") or "(не выбран)"),
        "Сопло           : %s мм" % cfg.get("nozzle", "0.4"),
        "Адрес принтера  : %s" % (cfg.get("print_host") or "(не задан — отправка по сети выключена)"),
        "Запись в Orca   : только после подтверждения в каждом запуске",
    ]
