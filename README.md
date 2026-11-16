<div align="center">

# Filament Lab

**Filament calibration inside OrcaSlicer. Pick a spool, open a test plate, slice, print, enter what you measured — the spool's preset is updated for you.**

[![CI](https://img.shields.io/github/actions/workflow/status/ValenokMC/OrcaSlicer-Calibration-Plugin/ci.yml?branch=main&style=flat-square)](https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin/actions)
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-2.5-F08A2A?style=flat-square)](#compatibility)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square&logo=windows&logoColor=white)](#compatibility)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

**English** · [Русский](README_RU.md)

[Changelog](CHANGELOG.md) · [Support](SUPPORT.md) · [Telegram](https://t.me/SupporBiBot?start=centauri_calibrator) · [Support the author](https://pay.cloudtips.ru/p/5440d07c)

</div>

---

Filament Lab is a plugin for **OrcaSlicer 2.5**. It adds a calibration tab to the
slicer and keeps one preset per spool. It replaces the console calibrator of
version 1.x, which is still available under the
[`v1.0.0` tag](https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin/releases/tag/v1.0.0).

> **Status: preview.** It is used for real calibrations on a Windows machine
> with an Elegoo Centauri Carbon. Other printers, a clean install on a fresh
> profile and the retraction flow are not verified yet — see [Compatibility](#compatibility).

## What it calibrates

| # | Test | What you enter | Preset field |
|---|---|---|---|
| 1 | **Temperature** | Temperature of the best tower block | `nozzle_temperature` |
| 2 | **Flow** | Label of the flattest tile | `filament_flow_ratio` |
| 3 | **Shrinkage** | Length of a 100 mm bar | `filament_shrink` |
| 4 | **Pressure advance** | Height of the sharpest band on the tower | `pressure_advance` |
| 5 | **Max volumetric flow** | Height where the wall starts to fail | `filament_max_volumetric_speed` |
| + | **Retraction** (optional) | Height of the cleanest step | `filament_retraction_length` |

Materials with scales: **PLA · PETG · PETG-CF · PETG-GF · ABS · ASA · PA · TPU**.

## How it works

- **A test opens as a ready plate.** The tab writes a 3MF with the test geometry
  and the settings that test needs, on top of the printer and process already
  selected in Orca. Temperature, flow, PA and max-flow models are taken from the
  OrcaSlicer installation itself; the shrinkage bar is this project's own.
- **You enter the raw measurement**, not the final number. The material scale
  turns it into a preset value and refuses values that make no physical sense.
- **The preset is an overlay.** Only the measured fields are written; the rest is
  inherited from the base profile, so a vendor profile update does not erase a
  calibration.
- **Other nozzles.** Variants `@0.2`, `@0.6` and `@0.8 nozzle` are derived from the
  0.4 result. They are estimates, marked as such, and can be re-measured.
- **No restart for new spools.** Spools live in a local preset bundle that Orca
  reloads on the fly.
- Retraction runs through Orca's own *Calibration → Retraction*; the tab shows the
  range to enter and stores the measurement.

## Install

There is no 2.x release archive yet. Build the single plugin file from source:

```powershell
git clone https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin.git
cd OrcaSlicer-Calibration-Plugin
python plugin/build.py dist/kalibrovka.py
```

Then in OrcaSlicer: **Plugins → Install local plugin** → `dist/kalibrovka.py`.
Orca installs the mesh libraries the plugin declares (`trimesh`, `numpy`,
`shapely`, `mapbox-earcut`, `DracoPy`, `scipy`). After replacing an installed
version, restart Orca.

Recommended Orca setting: *Preferences → Load behaviour → Load all*, so each
plate opens without the "project or geometry only" question.

## Compatibility

| | Status |
|---|---|
| OrcaSlicer 2.5.0, Windows 10 / 11 | ✅ Used daily |
| Elegoo Centauri Carbon, 0.4 mm nozzle | ✅ Calibrated end to end |
| Other printers in Orca | ⚠️ Plates follow the selected printer and bed size; a Prusa MINI profile sliced correctly, nothing else is tested |
| Clean install on a fresh Orca profile | ⚠️ Not yet checked |
| macOS, Linux | ❌ Not supported — the plate loader uses a Windows-only call |
| OrcaSlicer 2.4 and older | ❌ No plugin API — use the [console v1.0.0](https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin/releases/tag/v1.0.0) |

**Interface language:** Russian. An English interface is planned.

## Your data

```
%APPDATA%\OrcaSlicer\kalibrovka\
├── шкалы.json      test scales per material
├── Журнал.csv      one row per calibration
├── базы.json       snapshot of base profile values
└── Катушки\        measurements and plates per spool
```

Spool presets go to `%APPDATA%\OrcaSlicer\user\<account>\_local\kalibrovka\`.
Data stays inside Orca's own folder because Orca asks for permission for every
file a plugin touches outside it.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install trimesh numpy shapely mapbox-earcut DracoPy scipy
python -m pytest
python tools/check_public_safety.py
python tools/build_release.py --version 0.0.0-dev
```

Code map and the working plan (Russian): [plugin/README.md](plugin/README.md),
[plugin/СОСТОЯНИЕ.md](plugin/СОСТОЯНИЕ.md). See also [CONTRIBUTING.md](CONTRIBUTING.md).

## Support the author

If the plugin turned out to be useful: [☕ CloudTips](https://pay.cloudtips.ru/p/5440d07c)
· foreign card: [Tribute](https://web.tribute.tg/d/P54). Nothing is locked or paid for.

## License

[MIT](LICENSE) © ValenokMC. Third-party components and what is (not)
redistributed: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Not affiliated with Elegoo or the OrcaSlicer project; both names are used to say
what this works with.
