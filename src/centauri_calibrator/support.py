# -*- coding: utf-8 -*-
"""Links to the author, and the once-a-month note.

Same restraint as the Telegram bot, for the same reason: a tool that asks for
money every time you use it is a tool people stop using.

The browser is never opened on its own. The link is printed, and only opened if
the user says yes - a program that launches a payment page by itself has
crossed a line, however good its intentions.
"""
import json
import os
import time
import webbrowser

from . import paths


TRIBUTE_URL_TELEGRAM = "https://t.me/tribute/app?startapp=dP54"
TRIBUTE_URL_WEB = "https://web.tribute.tg/d/P54"

GITHUB_URL = "https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator"
ISSUES_URL = GITHUB_URL + "/issues"
SUPPORT_BOT_URL = "https://t.me/SupporBiBot?start=centauri_calibrator"

REMINDER_INTERVAL_DAYS = 30
REMINDER_INTERVAL_SEC = REMINDER_INTERVAL_DAYS * 86400

STATE_FILE = "support.json"

# Two lines. No more.
REMINDER_TEXT = ("Если калибратор оказался полезен, можно поддержать его развитие:\n"
                 "  " + TRIBUTE_URL_WEB)


def _state_path():
    return os.path.join(paths.data_dir(), STATE_FILE)


def load_state():
    try:
        with open(_state_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def mark_installed(when=None):
    """Stamp the install date once. Re-running setup must not reset it."""
    state = load_state()
    if not state.get("installed_at"):
        state["installed_at"] = when if when is not None else time.time()
        save_state(state)
    return state["installed_at"]


def due(state=None, now=None, interval_sec=REMINDER_INTERVAL_SEC):
    """Is the note due? Same three conditions as the bot's."""
    state = load_state() if state is None else state
    now = time.time() if now is None else now
    installed = state.get("installed_at")
    if not installed:
        return False
    if now - installed < interval_sec:
        return False
    last = state.get("last_reminder_at")
    if last and now - last < interval_sec:
        return False
    return True


def mark_shown(now=None):
    state = load_state()
    state["last_reminder_at"] = time.time() if now is None else now
    save_state(state)


def maybe_show(printer=print, now=None, dry_run=False):
    """Print the note if it is due. Returns True if it was shown.

    Never in a dry run: a dry run is a rehearsal, and asking for money during
    one would be asking for something the user did not do yet.
    """
    if dry_run or not due(now=now):
        return False
    printer("")
    printer(REMINDER_TEXT)
    mark_shown(now=now)
    return True


def about_lines():
    return [
        "Centauri Carbon Filament Calibrator",
        "",
        "  Документация  %s" % GITHUB_URL,
        "  Об ошибках    %s" % ISSUES_URL,
        "  Написать      %s" % SUPPORT_BOT_URL,
        "  Поддержать    %s" % TRIBUTE_URL_WEB,
    ]


def open_tribute(confirm=True, opener=webbrowser.open):
    """Open the support page - only after an explicit yes."""
    if not confirm:
        return False
    try:
        opener(TRIBUTE_URL_WEB)
        return True
    except Exception:
        return False
