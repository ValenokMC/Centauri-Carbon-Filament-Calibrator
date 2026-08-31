# -*- coding: utf-8 -*-
"""Identity of a calibration run and safe COSMOS preset names."""
import hashlib
import json

from . import names, orca


SCHEMA = 2
IDENTITY_FIELDS = (
    "firmware_backend", "nozzle", "machine_preset", "machine_fingerprint",
)


def from_config(cfg):
    backend = str(cfg.get("firmware_backend") or orca.BACKEND_STOCK).lower()
    if backend not in orca.BACKENDS:
        backend = "unknown"
    return {
        "firmware_backend": backend,
        "nozzle": str(cfg.get("nozzle") or orca.SUPPORTED_NOZZLE),
        "machine_preset": str(cfg.get("machine_preset") or ""),
        "machine_fingerprint": str(cfg.get("machine_fingerprint") or ""),
        "orca_app_version": str(cfg.get("orca_app_version") or ""),
        "profile_bundle_version": str(cfg.get("profile_bundle_version") or
                                      cfg.get("orca_version") or ""),
    }


def identity(context):
    return tuple(str((context or {}).get(key) or "") for key in IDENTITY_FIELDS)


def matches(left, right):
    return identity(left) == identity(right)


def key(context, length=10):
    body = json.dumps(identity(context), ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:length]


def folder_suffix(context):
    return "[%s-%s-%s]" % (
        str(context.get("firmware_backend") or "unknown").lower(),
        str(context.get("nozzle") or "?"), key(context, 8))


def preset_name(spool, context):
    """Keep stock names compatible; namespace COSMOS by exact profile."""
    spool = names.safe_name(spool)
    if context.get("firmware_backend") == orca.BACKEND_STOCK:
        return spool
    tag = "[%s %s %s]" % (
        str(context.get("firmware_backend") or "unknown").upper(),
        str(context.get("nozzle") or "?"), key(context, 8))
    room = max(1, names.MAX_LENGTH - len(tag) - 1)
    return names.safe_name("%s %s" % (spool[:room].rstrip(), tag))


def legacy_is_compatible(current):
    """Old context-free measurements were created only for stock 0.4."""
    return (current.get("firmware_backend") == orca.BACKEND_STOCK
            and str(current.get("nozzle")) == orca.SUPPORTED_NOZZLE)
