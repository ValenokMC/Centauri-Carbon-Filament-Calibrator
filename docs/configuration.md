# Configuration

## The file

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\config.json
```

Written by `Setup.cmd`. To change anything, re-run it — it offers every existing
answer as the default, so pressing Enter through the parts you do not want to
change is safe, and it never touches your journal, your measurements or your
preset backups.

| Key | What it is |
|---|---|
| `orca_install_dir` | Where OrcaSlicer is installed |
| `orca_version` | Legacy copy of the Elegoo profile bundle version, kept for v1.0 compatibility |
| `orca_app_version` | The installed OrcaSlicer application version |
| `profile_bundle_version` | The Elegoo profile bundle version |
| `firmware_backend` | `stock` for Elegoo/SDCP or `cosmos` for OpenCentauri/COSMOS/Moonraker |
| `machine_preset` | The exact printer preset you calibrate on |
| `machine_fingerprint` | Stable identity of that preset; network addresses and API keys are excluded |
| `print_host` | Legacy field from pre-release builds. Ignored by the live-wizard workflow. |
| `nozzle` | `"0.4"`. Nothing else is tested. |
| `write_to_orca` | Legacy compatibility field. It never grants permission; every new calibration run asks before its first preset write. |

`Doctor.cmd` prints all of it, in a readable form, without changing anything.

Changing firmware, nozzle or printer preset creates a separate calibration run
and a separate COSMOS filament-preset name. Measurements made with the stock
firmware are never silently resumed under COSMOS. Re-run `Setup.cmd` after any
of those changes.

---

# The scales file

`src/centauri_calibrator/scales.json` is the interesting one. It defines every
test for every material — what to print, within which limits, and how a
measurement becomes a value.

You can edit it. It is the intended way to correct a scale that does not match
your printer.

## Shape

```json
{
  "version": 1,
  "slicer": "OrcaSlicer",
  "printer": "Elegoo Centauri Carbon 0.4 nozzle",
  "nozzle": 0.4,
  "vendors": ["ELEGOO", "eSUN", "SUNLU", "..."],
  "materials": {
    "PLA": {
      "base": "Generic PLA @Elegoo Centauri",
      "drying": {"temperature": 45, "hours": 6},
      "tests": [ ... ]
    }
  }
}
```

## A test

```json
{
  "key": "temperature",
  "order": 1,
  "input": "direct",
  "params": {"start": 230, "end": 195, "step": -5, "block_height": 10},
  "fields": ["nozzle_temperature", "nozzle_temperature_initial_layer"],
  "limits": [175, 245],
  "file": "{material}/1_temperature.3mf",
  "question": "Температура, подписанная на лучшем блоке, °C",
  "hint": "...",
  "steps": ["...", "..."],
  "print_via": "Калибровка → Температурная башня",
  "after": "..."
}
```

| Field | Meaning |
|---|---|
| `key` | Identifies the test. Also the key under which your measurement is stored. |
| `order` | Running order. **Not cosmetic** — flow is measured at the final temperature, PA at the final flow, max flow at the final PA. |
| `input` | Which formula to use. See below. |
| `params` | The scale: what the plate actually prints. |
| `fields` | Which preset fields the result sets. |
| `limits` | The sanity bounds. A result outside them is refused. |
| `file` | Routing name. Five Orca wizard names are never reopened; the shrinkage name resolves to project-owned geometry. |
| `question`, `hint`, `steps`, `print_via`, `after` | Shown to the user. Russian. |
| `unverified` | `true` means the number is typical rather than measured here. The dialog warns. |

## Input kinds

| `input` | Formula | You enter |
|---|---|---|
| `direct` | none | the value as printed on the part |
| `offset` | `flow_by_offset` | the tile label, -0.05 to 0.05 |
| `wall_width` | `flow` | a measured wall thickness |
| `size` | `shrinkage` | a measured length |
| `blocks` | `by_blocks` | the height of the best block |
| `continuous` | `continuous` | the height where it failed |
| `table` | `by_table` | a height, resolved through an uneven step table |
| `number` | `by_number` | a line number, from zero |

## Correcting a scale

If a tower on your printer does not match what the scale says — different block
height, different starting temperature — edit `params` to describe what actually
printed, and clear `unverified` if it was set.

Two rules:

1. **Change `params` to match reality, not to make the answer come out.** The
   params describe the plate; if they are wrong, every measurement from that
   plate is wrong.
2. **Widen `limits` only if you are sure.** They are what catches a caliper
   reading off by a factor of ten. If a bound rejects a genuine result, please
   open an issue as well — that is a bug worth fixing for everybody.

After editing, run any test through `Dry-Run.cmd` — it computes and shows
everything without writing.

## Adding a vendor

Append to `vendors`. It only populates the menu; you can always choose
"Другой производитель" and type one.

The vendor is also read off the front of a spool name to fill `filament_vendor`
in the preset, so listing yours makes that come out right.
