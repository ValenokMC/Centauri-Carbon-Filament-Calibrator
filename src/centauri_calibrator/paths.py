# -*- coding: utf-8 -*-
"""Where user data lives.

Never inside the repository, and never inside the OrcaSlicer installation.
Everything the user accumulates - the journal, the spool measurements, the
personalised plates, the preset backups - belongs to them and has to survive an
update that replaces the program folder wholesale.
"""
import os


APP_DIR_NAME = "CentauriCarbonFilamentCalibrator"


def data_dir(create=True):
    r"""%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator, created on demand.

    CALIBRATOR_DATA_DIR overrides it; the test suite sets it to a temporary
    directory so a test run can never touch a real journal.
    """
    override = os.environ.get("CALIBRATOR_DATA_DIR")
    if override:
        base = override
    else:
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        base = os.path.join(local, APP_DIR_NAME)
    if create:
        os.makedirs(base, exist_ok=True)
    return base


def config_path(create=True):
    return os.path.join(data_dir(create=create), "config.json")


def journal_path(create=True):
    return os.path.join(data_dir(create=create), "Journal.csv")


def spools_dir(create=True):
    d = os.path.join(data_dir(create=create), "spools")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def generated_plates_dir(create=True):
    d = os.path.join(data_dir(create=create), "generated-plates")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def preset_backups_dir(create=True):
    d = os.path.join(data_dir(create=create), "preset-backups")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def logs_dir(create=True):
    d = os.path.join(data_dir(create=create), "logs")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def package_dir():
    return os.path.dirname(os.path.abspath(__file__))


def repo_root():
    return os.path.dirname(os.path.dirname(package_dir()))


def templates_dir():
    """Read-only templates shipped with the program. Never written to."""
    return os.path.join(repo_root(), "templates")
