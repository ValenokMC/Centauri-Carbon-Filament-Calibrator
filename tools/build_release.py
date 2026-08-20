#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Windows release archive, and check what went into it.

    python tools/build_release.py --version 1.0.0
    python tools/build_release.py --verify dist

The archive is built from an explicit allow-list, not by copying the repository
and deleting things afterwards. That distinction matters: a deny-list is only as
good as its last update, and the thing it would miss is exactly the thing that
must not ship.
"""
import argparse
import hashlib
import os
import shutil
import sys
import zipfile


ARCHIVE_STEM = "Centauri-Calibrator"

# Exactly what a user needs to run the program. Nothing else is copied.
INCLUDE_FILES = [
    "Setup.cmd",
    "Run.cmd",
    "Doctor.cmd",
    "Dry-Run.cmd",
    "Prepare-Templates.cmd",
    "About.cmd",
    "Open-Data-Folder.cmd",
    "_find-python.cmd",
    "Настроить.cmd",
    "Калибровать.cmd",
    "README.md",
    "README_RU.md",
    "CHANGELOG.md",
    "LICENSE",
    "SUPPORT.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "examples/Journal.example.csv",
    "docs/installation.md",
    "docs/calibration.md",
    "docs/templates.md",
    "docs/troubleshooting.md",
    "docs/security.md",
]

INCLUDE_TREES = [
    ("src/centauri_calibrator", ".py"),
    # The plates this project generates itself. The other five per material are
    # built on the user's machine by Prepare-Templates.cmd - see
    # THIRD_PARTY_NOTICES.md for why they are not shipped.
    ("templates", ".3mf"),
]

# Names that must never appear inside the archive, whatever the allow-list says.
# Belt and braces: if one of these turns up, the build is wrong.
FORBIDDEN_IN_ARCHIVE = (
    "config.json", "Journal.csv", "support.json", ".env",
    "__pycache__", ".pyc", ".git", "Journal.csv", ".pytest_cache",
)

# Files a user must find in the archive, or the release is broken.
REQUIRED_IN_ARCHIVE = (
    "Setup.cmd", "Run.cmd", "VERSION",
    "src/centauri_calibrator/__main__.py", "src/centauri_calibrator/session.py",
    "src/centauri_calibrator/scales.json",
    "templates/PLA/2b_shrinkage.3mf",
    "examples/Journal.example.csv", "LICENSE",
)


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect(root):
    """(archive_name, absolute_path) pairs, from the allow-list only."""
    items = []
    for relative in INCLUDE_FILES:
        full = os.path.join(root, *relative.split("/"))
        if not os.path.exists(full):
            raise SystemExit("missing from the repository: %s" % relative)
        items.append((relative, full))

    for tree, suffix in INCLUDE_TREES:
        base = os.path.join(root, *tree.split("/"))
        for directory, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in sorted(filenames):
                # .py trees carry their .json data files too (scales.json);
                # a .3mf tree carries only .3mf.
                allowed = (suffix, ".json") if suffix == ".py" else (suffix,)
                if suffix and not name.endswith(allowed):
                    continue
                full = os.path.join(directory, name)
                relative = os.path.relpath(full, root).replace(os.sep, "/")
                items.append((relative, full))
    return items


def build(version, out_dir):
    root = repo_root()
    os.makedirs(out_dir, exist_ok=True)
    name = "%s-v%s-windows" % (ARCHIVE_STEM, version)
    archive = os.path.join(out_dir, name + ".zip")

    items = collect(root)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for relative, full in items:
            z.write(full, "%s/%s" % (name, relative))
        # A version the running program and a bug report can both point at.
        z.writestr("%s/VERSION" % name, version + "\n")

    digest = sha256(archive)
    sums = os.path.join(out_dir, "SHA256SUMS.txt")
    with open(sums, "a" if os.path.exists(sums) else "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (digest, os.path.basename(archive)))

    print("built  %s" % archive)
    print("       %d files, %.1f KB" % (len(items) + 1,
                                        os.path.getsize(archive) / 1024.0))
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

        if not failed:
            print("  ok    %d entries, nothing forbidden, everything required"
                  % len(names))
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
