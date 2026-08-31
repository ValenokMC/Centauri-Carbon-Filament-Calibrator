# Installation

## 1. Python

From [python.org/downloads](https://www.python.org/downloads/), 3.9 or newer.

> [!IMPORTANT]
> Tick **"Add python.exe to PATH"** on the first installer screen. Missing it is
> the most common reason a launcher says `Python not found`.

## 2. OrcaSlicer

You need **OrcaSlicer 2.4.2** with the **Elegoo** vendor profiles installed. If
you are already printing on this machine, you have both.

Other versions are not tested. Profile paths and configuration key names move
between OrcaSlicer releases, so a different version may work perfectly or may
fail in a way that produces plausible but wrong numbers. `Doctor.cmd` tells you
which version it found.

## 3. Download and unpack

Take the ZIP from the
[latest release](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/releases/latest)
and unpack it anywhere. Paths with spaces or Cyrillic characters are fine.

Do not run it from inside the ZIP.

## 4. Run the wizard

Double-click **`Setup.cmd`** (or `Настроить.cmd`). Eight setup steps:

| Step | What it does |
|---|---|
| 1. OrcaSlicer | Looks in the usual install locations; lets you point at it if it is elsewhere. |
| 2. Version | Reads the OrcaSlicer application version and the Elegoo profile bundle version separately. |
| 3. System profiles | Counts the Elegoo filament profiles it can see. |
| 4. User folders | Lists every OrcaSlicer account folder — usually `default`, plus one per signed-in account. |
| 5. Firmware | Records stock Elegoo/SDCP or OpenCentauri/COSMOS/Moonraker. |
| 6. Printer preset | Finds the 0.4 mm Centauri preset for that firmware; asks you to choose if there are several. |
| 7. Write access | Checks it can actually write to the preset folders. |
| 8. Data folder | Creates your data directory. |

Then a summary, and it asks whether to save.

**Nothing is written to OrcaSlicer during setup.** The first write happens during
a calibration, after its own separate confirmation.

### About steps 5 and 6

The system profile is `Elegoo Centauri Carbon 0.4 nozzle`. Many people also
have their own preset inheriting from it.

If you have several — one per nozzle, firmware, or a variant for manual colour
changes — the wizard asks. Choose the exact one you actually print with. For
COSMOS, import its official 0.4 mm Moonraker printer profile first; setup stops
safely if it can see only the stock Elegoo profile.

### About step 7

If the write check fails, OrcaSlicer was probably installed by a different
Windows user. Calibration still works — the arithmetic and measurements —
but you will have to move the preset file into place yourself. The program tells
you exactly where it wanted to put it.

## 5. Calibrate

**`Калибровать.cmd`** (or `Run.cmd`).

Choose the material, name the spool, and work through the tests. For
temperature, flow, pressure advance, max flow and retraction, start the test
from OrcaSlicer's **Calibration** menu while it is open. The program gives the
exact range and step. Slice and print in that same live wizard session; do not
save and reopen the generated tower as a reusable project.

After every accepted measurement the program asks permission to update the
spool preset. Restart OrcaSlicer and select that updated preset before starting
the next test. The project-owned shrinkage bar opens automatically.

Why this matters is in [templates.md](templates.md); the test-by-test guide is
in [calibration.md](calibration.md).

Try **`Dry-Run.cmd`** first if you want to see the whole dialog without anything
being written.

## Where your data lives

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\
├── config.json          what setup found
├── Journal.csv          one row per calibrated spool
├── spools\              measurements, per spool, per run
│   └── 2026-01-15 ExampleBrand Demo PLA\
│       └── measurements.json
├── preset-backups\      every preset replaced, timestamped
├── support.json         date of the optional monthly support note
└── logs\
```

`Open-Data-Folder.cmd` prints the path.

Deliberately outside the program folder: you can replace the program with a new
version and lose nothing.

## Updating

Unpack the new ZIP over the old folder. Your data, journal, measurements and
preset backups are elsewhere and are untouched.

Re-run `Setup.cmd` only if you changed something about your OrcaSlicer setup.
That includes changing firmware, nozzle or printer preset. Existing measurements
remain on disk, but a different machine context starts a separate run.

## Uninstalling

1. Delete the program folder.
2. Delete `%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\` if you want your
   journal and measurements gone too.
3. Your calibrated presets stay in OrcaSlicer — they are ordinary filament
   presets and keep working. Delete them from within Orca if you want them gone.

Nothing is written to the registry and nothing is installed system-wide.
