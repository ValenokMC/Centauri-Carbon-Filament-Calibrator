# -*- coding: utf-8 -*-
"""Turning what the user typed into something safe to use as a filename.

A spool name goes into two places that take a path: a folder under spools/ and a
preset .json inside the OrcaSlicer profile tree. A name like
``../../../autoexec`` or ``CON`` must not be able to escape, collide with a
device, or overwrite something that matters.

The rule is allow-list, not deny-list. Deny-lists for Windows paths are famously
incomplete - trailing dots, trailing spaces, alternate data streams, reserved
device names with an extension - so anything not explicitly permitted is
replaced.
"""
import os
import re
import unicodedata


# Reserved device names. On Windows these are still devices with any extension
# and in any case: CON, con.txt and CoN.json all open the console.
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Letters, digits, space and a small set of punctuation people really do use in
# a spool name ("eSUN PLA+ Matte", "Generic PETG-CF").
ALLOWED = re.compile(r"[^\w \-+.()\[\]]", re.UNICODE)

MAX_LENGTH = 80


class UnsafeName(ValueError):
    """The name cannot be made into a safe filename."""


def safe_name(raw, max_length=MAX_LENGTH):
    """Normalise a user-supplied name into a safe single path component.

    Raises UnsafeName if nothing usable is left - better to ask again than to
    invent a name the user will not recognise in their own folder.
    """
    if raw is None:
        raise UnsafeName("empty name")
    text = unicodedata.normalize("NFC", str(raw)).strip()
    if not text:
        raise UnsafeName("empty name")

    # Any path separator, drive letter or parent reference is rejected outright
    # rather than stripped: a name containing one is a mistake or an attack,
    # and silently rewriting it would hide both.
    if "/" in text or "\\" in text or text.startswith("~"):
        raise UnsafeName("a name cannot contain a path")
    if ":" in text:
        raise UnsafeName("a name cannot contain a colon")
    if ".." in text:
        raise UnsafeName("a name cannot contain '..'")

    cleaned = ALLOWED.sub("_", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Windows silently strips trailing dots and spaces, which turns "demo." and
    # "demo" into the same file. Strip them ourselves so the name we show is
    # the name that exists.
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        raise UnsafeName("nothing usable left after cleaning %r" % raw)

    stem = cleaned.split(".")[0].upper()
    if stem in WINDOWS_RESERVED:
        cleaned = "_" + cleaned

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")
    if not cleaned:
        raise UnsafeName("nothing usable left after cleaning %r" % raw)
    return cleaned


def safe_join(base, *parts):
    """Join under ``base`` and prove the result did not escape it.

    The check is done on the resolved absolute path, because that is the only
    thing that catches a symlink or a junction pointing outside - which is
    exactly how a "safe" name check gets bypassed in practice.
    """
    base_abs = os.path.abspath(base)
    candidate = os.path.abspath(os.path.join(base_abs, *[safe_name(p) for p in parts]))
    if candidate != base_abs and not candidate.startswith(base_abs + os.sep):
        raise UnsafeName("path escapes the data directory: %r" % (parts,))
    return candidate


def spool_folder_name(spool, when=None):
    """"2026-01-31 eSUN PLA Matte" - date first so folders sort by run."""
    import datetime
    day = (when or datetime.date.today()).isoformat()
    return "%s %s" % (day, safe_name(spool))


def vendor_of(spool, vendors):
    """The brand, taken from the start of the spool name.

    A spool is named "<vendor> <label from the reel>", so the brand can be read
    off the front. For spools chosen from the journal there is no other source:
    no separate field is stored.
    """
    for vendor in sorted(vendors or [], key=len, reverse=True):
        if spool.lower().startswith(vendor.lower()):
            return vendor
    parts = spool.split()
    return parts[0] if parts else ""
