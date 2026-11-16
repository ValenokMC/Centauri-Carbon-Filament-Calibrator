#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Filament Lab release archive, and check what went into it.

    python tools/build_release.py --version 2.0.0
    python tools/build_release.py --verify dist

The archive holds the single plugin file built by plugin/build.py plus the
documents a user needs. It is assembled from an explicit allow-list, not by
copying the repository and deleting things afterwards: a deny-list is only as
good as its last update, and what it would miss is exactly what must not ship.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import zipfile


ARCHIVE_STEM = "Filament-Lab"
PLUGIN_FILE = "kalibrovka.py"

# Documents shipped next to the plugin file. Nothing else is copied.
INCLUDE_FILES = [
    "README.md",
    "README_RU.md",
    "CHANGELOG.md",
    "LICENSE",
    "SUPPORT.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
]

# Names that must never appear inside the archive, whatever the allow-list says.
FORBIDDEN_IN_ARCHIVE = (
    "config.json", "Journal.csv", "Журнал.csv", ".env",
    "__pycache__", ".pyc", ".git", ".pytest_cache", "_Локальное",
)

# Files a user must find in the archive, or the release is broken.
REQUIRED_IN_ARCHIVE = (PLUGIN_FILE, "VERSION", "README.md", "LICENSE",
                       "THIRD_PARTY_NOTICES.md")


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_plugin(root, out_dir):
    """Run plugin/build.py and return the path of the single plugin file."""
    target = os.path.join(out_dir, PLUGIN_FILE)
    subprocess.run([sys.executable, "-B", os.path.join(root, "plugin", "build.py"), target],
                   check=True)
    return target


def build(version, out_dir):
    root = repo_root()
    os.makedirs(out_dir, exist_ok=True)
    name = "%s-v%s-windows" % (ARCHIVE_STEM, version)
    archive = os.path.join(out_dir, name + ".zip")

    items = [(PLUGIN_FILE, build_plugin(root, out_dir))]
    for relative in INCLUDE_FILES:
        full = os.path.join(root, *relative.split("/"))
        if not os.path.exists(full):
            raise SystemExit("missing from the repository: %s" % relative)
        items.append((relative, full))

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for relative, full in items:
            z.write(full, "%s/%s" % (name, relative))
        # A version the user and a bug report can both point at.
        z.writestr("%s/VERSION" % name, version + "\n")

    digest = sha256(archive)
    sums = os.path.join(out_dir, "SHA256SUMS.txt")
    with open(sums, "a" if os.path.exists(sums) else "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (digest, os.path.basename(archive)))

    print("built  %s" % archive)
    print("       %d files, %.1f KB" % (len(items) + 1, os.path.getsize(archive) / 1024.0))
    print("sha256 %s" % digest)
    return archive


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(target):
    """Check an archive holds what it must and nothing it must not."""
    archives = []
    if os.path.isdir(target):
        archives = [os.path.join(target, n) for n in sorted(os.listdir(target))
                    if n.endswith(".zip")]
    elif os.path.isfile(target):
        archives = [target]
    if not archives:
        print("no archive found in %s" % target)
        return 1

    failed = False
    for archive in archives:
        print("\nchecking %s" % os.path.basename(archive))
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            stripped = ["/".join(n.split("/")[1:]) for n in names]
            plugin = [n for n in names if n.endswith("/" + PLUGIN_FILE)]
            source = z.read(plugin[0]).decode("utf-8") if plugin else ""

        for forbidden in FORBIDDEN_IN_ARCHIVE:
            hits = [n for n in names if forbidden in n]
            if hits:
                failed = True
                print("  FAIL  contains %s (%d entr%s)"
                      % (forbidden, len(hits), "y" if len(hits) == 1 else "ies"))

        for required in REQUIRED_IN_ARCHIVE:
            if required not in stripped:
                failed = True
                print("  FAIL  missing %s" % required)

        # The plugin file must be the built one: every build marker replaced.
        leftovers = [m for m in ('"@@PAGE@@"', '"@@TAB_ICON@@"', "# @@ШКАЛЫ@@", "# @@МОДЕЛИ@@")
                     if m in source]
        if source and leftovers:
            failed = True
            print("  FAIL  %s was not built: %s" % (PLUGIN_FILE, ", ".join(leftovers)))
        if source and "[tool.orcaslicer.plugin]" not in source:
            failed = True
            print("  FAIL  %s has no OrcaSlicer plugin header" % PLUGIN_FILE)

        if not failed:
            print("  ok    %d entries, nothing forbidden, everything required" % len(names))
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--version", default="0.0.0-dev")
    parser.add_argument("--out", default=os.path.join(repo_root(), "dist"))
    parser.add_argument("--verify", metavar="PATH",
                        help="check an existing archive or directory instead")
    args = parser.parse_args(argv)

    if args.verify:
        return verify(args.verify)

    archive = build(args.version, args.out)
    return verify(archive)


if __name__ == "__main__":
    sys.exit(main())
