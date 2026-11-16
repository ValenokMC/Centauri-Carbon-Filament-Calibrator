# Security

## Reporting a vulnerability

**Do not open a public issue.**

Use [GitHub's private vulnerability reporting](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/security/advisories/new),
or write to [@SupporBiBot](https://t.me/SupporBiBot?start=centauri_calibrator)
and ask for a private channel.

Expect an acknowledgement within about a week. One-person project; no security
team, no formal SLA. Please allow a reasonable time for a fix before disclosing.

## What the plugin can touch

Filament Lab runs inside OrcaSlicer, under Orca's plugin permissions. Orca asks
the user before a plugin reads or writes a file outside Orca's own folder, so the
plugin keeps everything inside it:

| Place | What is written | If it goes wrong |
|---|---|---|
| `%APPDATA%\OrcaSlicer\kalibrovka\` | Scales, journal, measurements, plates per spool | Only the plugin depends on it |
| `%APPDATA%\OrcaSlicer\user\<account>\_local\kalibrovka\` | Filament presets of calibrated spools | A broken preset affects that spool only; the base profile is untouched |

Removing a spool in the tab **moves** its data and presets into an archive folder
inside the data directory; it does not delete them.

The plugin makes **no network connections** of its own. Slicing, sending to the
printer and everything else on the network is done by OrcaSlicer.

## Privacy

- Plates written by the tab carry the test geometry and test settings, **not**
  your printer settings or `print_host`.
- `tools/check_public_safety.py` scans the repository and every release archive
  (including the inside of ZIP and 3MF files) for private addresses, user paths
  and secrets. It runs in CI and before a release is built.
- **No telemetry.** Nothing is measured, counted or sent anywhere.

## The printer's network

> [!WARNING]
> Many printers' network services, the Centauri Carbon's among them, have **no
> authentication**. Do not forward their ports to the internet, and do not put
> them on a network you do not control.

## Supported versions

The latest commit on `main`. Version 1.x (the console calibrator) is no longer
maintained.
