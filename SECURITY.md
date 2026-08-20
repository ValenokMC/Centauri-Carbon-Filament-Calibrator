# Security

## Reporting a vulnerability

**Do not open a public issue.**

Use [GitHub's private vulnerability reporting](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/security/advisories/new),
or write to [@SupporBiBot](https://t.me/SupporBiBot?start=centauri_calibrator)
and ask for a private channel.

Expect an acknowledgement within about a week. One-person project; no security
team, no formal SLA. Please allow a reasonable time for a fix before disclosing.

## What this program can damage

Being honest about this is more useful than a list of reassurances. The
calibrator writes to three kinds of place, in increasing order of consequence.

### 1. Its own data directory — harmless

`%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\`. Yours, and nothing else
depends on it.

### 2. Your OrcaSlicer filament presets — recoverable

This is the only write outside its own folder, and it is guarded:

| Guard | Why |
|---|---|
| The exact path is printed and confirmed | You see what will happen before it does |
| The existing file is copied to `preset-backups\` first | Timestamped, never overwritten |
| The JSON is serialised and re-parsed before anything is touched | An unserialisable preset fails here, not half way through replacing a working file |
| Written to a temporary file, then `os.replace` | Atomic on Windows — there is no moment where a half-written file exists |
| On any failure, the original is still there | There is a test asserting the file's hash is unchanged after a failed write |

A corrupt filament preset stops OrcaSlicer from starting, which is why this is
built the way it is rather than with a plain `open(path, "w")`.

### 3. A running OrcaSlicer — your work

Presets are held in memory by Orca and read only at start-up, so it has to be
closed before a preset is written, or it may write its own copy back over ours.

**It is never force-killed.** `taskkill` without `/F` asks it to close; Orca
decides what to prompt about. If it does not exit within the timeout — usually
because it is asking about an unsaved project — the calibrator stops and asks
you to deal with it. It does not proceed while the state is uncertain.

A `/F` here would discard an unsaved project without asking, and a calibration
run is hours of your time. That trade is not close.

## Path safety

A spool name goes into three paths: a folder, a `.3mf`, and a preset filename.
`names.safe_name()` is allow-list based, not deny-list:

- path separators, drive letters, `..` and `~` are **refused**, not stripped —
  a name containing one is a mistake or an attack, and rewriting it silently
  would hide both
- Windows reserved device names (`CON`, `PRN`, `COM1`…) are defused, in any case
  and with any extension
- trailing dots and spaces are removed, because Windows removes them silently
  and two different names would become one file
- anything outside the permitted character set is replaced
- `safe_join()` resolves the final path and proves it did not escape the data
  directory — which is what catches a symlink or junction pointing outside

## Privacy

### What the .3mf files contain

OrcaSlicer stores `print_host` — your printer's network address — inside a saved
project. That is the leak this project was designed around.

- **Templates shipped here contain no address.** There is a test that opens
  every `.3mf` in the repository and asserts it.
- **Templates you build are sanitised on the way in.** `Prepare-Templates.cmd`
  strips `print_host` and any personal preset name from what you save.
- **Your address goes only into your personal copy**, in your own data folder,
  and only if you have one configured.
- **`tools/check_public_safety.py` opens every `.3mf`** — they are ZIP archives —
  and fails the build if one carries an address. This runs in CI and before a
  release is built.

### No telemetry

Nothing is measured, counted, or sent anywhere. The author cannot tell whether
you use the program or whether you ever opened the support link.

### Your journal is yours

`Journal.csv` records every spool you have calibrated, with dates. It stays in
your data folder. The repository ships `examples/Journal.example.csv` with
entirely invented values instead.

## The printer's network

The calibrator only writes an address into a project file; OrcaSlicer does the
sending. But the same warning applies as for anything touching this printer:

> [!WARNING]
> The Centauri Carbon's network services have **no authentication**. Do not
> forward its ports to the internet, and do not put it on a network you do not
> control.

## Supported versions

The latest release only.
