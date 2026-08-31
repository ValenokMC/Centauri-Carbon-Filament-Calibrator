# Security notes for users

[SECURITY.md](../SECURITY.md) is the policy and the design detail. This is the
practical version.

## The `.3mf` problem

> [!CAUTION]
> **OrcaSlicer stores your printer's network address inside a saved project.**
> A `.3mf` you saved yourself may contain `print_host`. If you attach one to an
> issue, a forum post, or a model-sharing site, you are publishing your internal
> network layout.

This project is built around that fact:

- **Nothing shipped here contains an address.** A test opens every `.3mf` in the
  repository and asserts it; the safety scanner does the same before a release.
- **Saved Orca wizard projects are never imported or reopened.** The five
  dynamic tests start directly from Orca's Calibration menu.
- **The included shrinkage bar is bare project-owned geometry.** It contains no
  printer, account, network or filament-preset settings.
- An old `print_host` field in local `config.json` is ignored; the current
  workflow does not copy it into a model.

To check a `.3mf` yourself: it is a ZIP. Rename it, open it, and read
`Metadata/project_settings.config`. Search for `print_host`.

## What is safe to share

| | |
|---|---|
| ✅ `Doctor.cmd` output | Replace your Windows user name with `USER` if you prefer |
| ✅ One row from your journal | The whole file is a record of every spool you own |
| ✅ Your measurements and the computed values | That is the useful part of a bug report |
| ✅ The included shrinkage model | Bare project-owned geometry, scanned before release |
| ❌ A `.3mf` you saved from Orca yourself | May carry your printer's address |
| ❌ Your whole `Journal.csv` | Dates and brands of everything you have printed |
| ❌ Your OrcaSlicer profile folder | Printer address and account id |

## What the program writes, and where

Three places, in increasing order of consequence:

**Its own data folder.** `%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\`.
Yours; nothing depends on it.

**Your OrcaSlicer filament presets.** The only write outside its own folder. You
see the exact path and confirm it, the existing file is backed up first, the new
content is validated as JSON, and it is written to a temporary file and moved
into place atomically. If anything fails, the original is untouched.

**Nothing else.** It does not modify the OrcaSlicer installation, does not touch
your process or machine presets, and does not change any Orca setting.

## Firmware and profile separation

Every measurement run records the firmware backend, nozzle, exact machine
preset and a fingerprint of that preset. A stock-firmware run cannot be resumed
under COSMOS, and a changed machine profile starts a new run. Old context-free
measurements are accepted only as stock-firmware 0.4 mm data.

COSMOS filament presets include the backend, nozzle and profile fingerprint in
their filename. Their `compatible_printers` list contains only the selected
COSMOS machine preset, so they cannot overwrite or attach themselves to the
stock Elegoo machine by name collision. Printer addresses, web UI URLs and API
keys are excluded from the fingerprint and are never copied into the preset.

## Closing OrcaSlicer

Presets are held in memory by Orca and read only at start-up, so it has to be
closed before a preset is written — otherwise it may write its own copy back
over yours on exit.

**It is asked, never forced.** `taskkill` without `/F`, so Orca can still prompt
you about an unsaved project. If it does not exit, the program stops and asks
you to deal with it rather than proceeding.

A forced kill would discard an unsaved project silently. A calibration is hours
of work; that trade is not close.

## Recovering a preset

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\preset-backups\
```

Every replaced preset is copied there with a timestamp before it is overwritten.
Copy one back into the Orca filament folder and restart Orca.

## Dry run

`Dry-Run.cmd` walks the whole dialog and writes nothing at all — no preset, no
journal entry, no measurement file. Use it to see what would happen.

The support reminder is suppressed in a dry run too. Asking for money for
something you have not actually done would be worse than not asking.

## What the program does not do

- **No telemetry.** Nothing is counted or sent anywhere. Whether you use it, and
  whether you ever opened the support link, is not knowable from here.
- **No network access of its own.** OrcaSlicer or the user's USB workflow
  handles printing.
- **No auto-update.** It never downloads or runs anything.
- **No third-party runtime dependencies.**
- **The browser is never opened on its own.** `About.cmd` prints the link and
  asks before opening it.

## Your printer's network

> [!WARNING]
> The Centauri Carbon's network services have **no authentication**. Anyone who
> can reach them can control the printer. Do not forward its ports to the
> internet, and do not put it on a network you do not control.

This is a property of the printer, not of this program, and it is worth knowing
whatever software you use with it.
