# -*- coding: utf-8 -*-
"""Console input and output, shared by the wizard and the calibration session.

Kept in one module so every prompt behaves the same way: Enter always takes the
default, and the default is always shown.
"""

BOLD, DIM, RED, GREEN, YELLOW, RESET = (
    "\033[1m", "\033[90m", "\033[31m", "\033[32m", "\033[33m", "\033[0m")


class Cancelled(Exception):
    """The user pressed Ctrl+C or closed stdin."""


# Yes and no in both keyboard layouts. Words typed in the wrong layout land
# here too: "да" on an English layout gives "lf", "нет" gives "ytn".
#
# What is deliberately NOT here: the Y key on a Russian layout types "н", and
# H on an English one types "y". Treating "н" as agreement would break an
# honest Russian "нет", so that pair is left alone. Enter is the answer for
# those cases - it always takes the default, shown as a capital letter.
YES = {"д", "да", "y", "yes", "l", "lf", "нуы", "1", "+"}
NO = {"н", "нет", "n", "no", "т", "ytn", "тщ", "0", "-"}


def say(text=""):
    print(text)


def head(text):
    say("\n%s%s%s" % (BOLD, text, RESET))


def ok(text):
    say("  %s✓%s %s" % (GREEN, RESET, text))


def warn(text):
    say("  %s!%s %s" % (YELLOW, RESET, text))


def bad(text):
    say("  %s✗%s %s" % (RED, RESET, text))


def dim(text):
    say("  %s%s%s" % (DIM, text, RESET))


def _input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        raise Cancelled()


def ask(prompt, default=None):
    tail = " [%s]" % default if default else ""
    while True:
        raw = _input("  %s%s: " % (prompt, tail)).strip()
        if raw:
            return raw
        if default is not None:
            return default


def ask_yes(prompt, default=None):
    hint = {True: " [Д/н]", False: " [д/Н]", None: " [д/н]"}[default]
    while True:
        raw = _input("  %s%s: " % (prompt, hint)).strip().lower()
        if not raw and default is not None:
            return default
        if raw in YES:
            return True
        if raw in NO:
            return False
        hint_text = ("Enter — вариант по умолчанию" if default is not None
                     else "нужно «д» или «н»")
        bad("Не понял ответ «%s». %s." % (raw, hint_text))


def ask_number(prompt, hint=None, previous=None):
    """A number. Enter keeps what is there, '-' erases the measurement."""
    if hint:
        dim(hint)
    tail = " [было %s]" % previous if previous is not None else ""
    while True:
        raw = _input("  %s%s: " % (prompt, tail)).strip()
        if not raw:
            return previous
        if raw == "-":
            return None
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            bad("Нужно число. Enter — оставить, «-» — стереть.")


def ask_text(prompt, default=None):
    while True:
        raw = _input("  %s%s: " % (prompt, (" [%s]" % default) if default else "")).strip()
        if raw:
            return raw
        if default:
            return default


def menu(title, items):
    """Numbered choice. items: list of (key, label). Returns the key."""
    say("\n%s%s%s" % (BOLD, title, RESET))
    for number, (_, label) in enumerate(items, start=1):
        say("  %2d  %s" % (number, label))
    while True:
        raw = _input("  Номер: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1][0]
        bad("Нужен номер от 1 до %d." % len(items))
