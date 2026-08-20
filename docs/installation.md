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

Double-click **`Setup.cmd`** (or `Настроить.cmd`). Eight read-only steps:

| Step | What it does |
|---|---|
| 1. OrcaSlicer | Looks in the usual install locations; lets you point at it if it is elsewhere. |
| 2. Version | Reads the Elegoo profile bundle version, and says which version this project was tested on. |
| 3. System profiles | Counts the Elegoo filament profiles it can see. |
| 4. User folders | Lists every OrcaSlicer account folder — usually `default`, plus one per signed-in account. |
| 5. Printer preset | Finds your Centauri Carbon presets; asks you to choose if there are several. |
| 6. Printer address | Picks up `print_host` if you already configured network sending. Optional. |
| 7. Write access | Checks it can actually write to the preset folders. |
| 8. Data folder | Creates your data directory. |

Then a summary, and it asks whether to save.

**Nothing is written to OrcaSlicer during setup.** The first write happens during
a calibration, after its own separate confirmation.

### About step 5

The system profile is `Elegoo Centauri Carbon 0.4 nozzle`. Most people also have
their own preset inheriting from it — that is where the network address lives,
so if you ever set up printing over the network, you have one.

If you have several — one per nozzle, or a variant for manual colour changes —
the wizard asks. Choose the one you actually print with.

### About step 6

**Having no address configured is normal and fully supported.** Plenty of people
slice to a USB stick. Without it, everything works; the plates just do not get
sent over the network.

If you do have one, it goes only into your own personalised plate copies, in
your own data folder. It never touches anything this project publishes.

### About step 7

If the write check fails, OrcaSlicer was probably installed by a different
Windows user. Calibration still works — the arithmetic, the journal, the plates —
but you will have to move the preset file into place yourself. The program tells
you exactly where it wanted to put it.

## 5. Build the calibration plates

Run **`Prepare-Templates.cmd`** once.

Save and import one plate from OrcaSlicer's own calibration wizard first. Its
sanitised settings become a local donor; the program then generates the
shrinkage project and walks you through the remaining tests. About ten minutes
for one material.

This step exists because those five are OrcaSlicer's models and their
redistribution terms are not stated anywhere this project can point to. The full
reasoning is in [templates.md](templates.md); the short version is that you
already have OrcaSlicer, so you already have the models, and building them
locally is the honest way to use them.

You do not have to do every material — build the ones you print.

## 6. Calibrate

**`Калибровать.cmd`** (or `Run.cmd`).

Choose the material, name the spool, and work through the plates. The
step-by-step guide for each test is in [calibration.md](calibration.md).

Try **`Dry-Run.cmd`** first if you want to see the whole dialog without anything
being written.

## Where your data lives

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\
├── config.json          what setup found
├── Journal.csv          one row per calibrated spool
├── spools\              measurements, per spool, per run
│   └── 2026-01-15 ExampleBrand Demo PLA\
│       ├── measurements.json
│       └── (your personalised plates for that run)
├── templates\           the plates you built
├── generated-plates\    personalised copies
├── preset-backups\      every preset replaced, timestamped
└── logs\
```

`Open-Data-Folder.cmd` prints the path.

Deliberately outside the program folder: you can replace the program with a new
version and lose nothing.

## Updating

Unpack the new ZIP over the old folder. Your data, your journal and your
locally-built templates are elsewhere and are untouched.

Re-run `Setup.cmd` only if you changed something about your OrcaSlicer setup.

## Uninstalling

1. Delete the program folder.
2. Delete `%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\` if you want your
   journal and measurements gone too.
3. Your calibrated presets stay in OrcaSlicer — they are ordinary filament
   presets and keep working. Delete them from within Orca if you want them gone.

Nothing is written to the registry and nothing is installed system-wide.
