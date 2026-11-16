## What this is

**Filament Lab** — a filament calibration tab for OrcaSlicer 2.5. Pick a spool,
open a test plate, slice and print it in Orca, enter what you measured, and the
spool's filament preset is updated.

## Install

1. Download `Filament-Lab-v<version>-windows.zip` and unpack it.
2. In OrcaSlicer: **Plugins → Install local plugin** → `kalibrovka.py`.
3. Restart Orca if a previous version was installed.

Orca installs the mesh libraries the plugin declares. Data and presets stay in
`%APPDATA%\OrcaSlicer`.

## Changes

<!-- From CHANGELOG.md -->

## Compatibility

- OrcaSlicer 2.5, Windows 10 / 11
- Calibrated end to end on an Elegoo Centauri Carbon with a 0.4 mm nozzle
- Other printers follow the selected Orca profile but are not verified

## Known limitations

<!-- Keep honest: what was not tested for this release. -->

## Verifying the download

    certutil -hashfile <file>.zip SHA256

and compare with `SHA256SUMS.txt`.

---

Full changelog: [CHANGELOG.md](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/blob/main/CHANGELOG.md)
