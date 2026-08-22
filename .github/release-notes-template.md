## What this is

The first public release of a guided filament-calibration workflow for the
Elegoo Centauri Carbon and OrcaSlicer. Measure the printed tests and the tool
creates or updates a filament preset without editing Python or JSON by hand.

## Changes

- Guided `Setup.cmd` discovers OrcaSlicer, account folders and compatible
  Centauri Carbon printer presets without modifying them.
- Temperature, flow, pressure advance, maximum flow, retraction and shrinkage
  workflows with the established formulas and scales.
- `Dry-Run.cmd` exercises the dialog without writing; `Doctor.cmd` provides a
  read-only environment report.
- Atomic preset updates with timestamped backups, path-safe spool names and
  user data stored outside the program folder.
- Tribute support is available from `About.cmd`, with one unobtrusive note after
  a successful preset save at most once per month.

## Fixes

- OrcaSlicer's five built-in calibration tests now start from the live
  Calibration menu, preserving the session-only calibration modes.
- Saved wizard projects with lost calibration state are rejected; the
  project-owned shrinkage bar remains available from disk.
- Public-safety checks inspect every shipped `.3mf` and the final ZIP for
  printer addresses or private data.

## Compatibility

- Windows 10 / 11
- Python 3.9 or newer
- OrcaSlicer 2.4.2 verified
- Elegoo Centauri Carbon with a 0.4 mm nozzle verified

## Known limitations

- Other OrcaSlicer releases, nozzle sizes, Centauri Carbon 2, macOS and Linux
  have not yet been verified.
- Built-in Orca calibration modes must be started from the live menu; only the
  included shrinkage model is opened from disk.

## Updating from the previous version

This is the first public release. For later updates, unpack the new ZIP over the
old program folder; measurements, backups and settings in `%LOCALAPPDATA%` are
not touched.

## Verifying the download

    certutil -hashfile <file>.zip SHA256

and compare with `SHA256SUMS.txt`.

---

Full changelog: [CHANGELOG.md](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/blob/main/CHANGELOG.md)
