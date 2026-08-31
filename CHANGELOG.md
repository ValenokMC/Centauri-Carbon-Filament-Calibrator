# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Separate stock Elegoo/SDCP and OpenCentauri/COSMOS/Moonraker setup contexts.
- Versioned measurement files and journal columns that record firmware, nozzle,
  exact machine preset, profile fingerprint and Orca/profile-bundle versions.
- Read-only diagnostics for the application version, profile bundle and every
  discovered machine context.

### Changed

- Setup now reads the OrcaSlicer application version separately from the Elegoo
  profile bundle version and requires an exact 0.4 mm COSMOS profile when that
  backend is selected.
- COSMOS filament presets are namespaced by backend/nozzle/profile and are
  compatible only with the selected COSMOS printer preset.
- A firmware, nozzle or machine-profile change starts a separate calibration
  run. Legacy context-free measurements remain valid only for stock 0.4 mm.

### Fixed

- Print-host discovery no longer picks an arbitrary profile when several
  equally plausible Centauri presets exist.

## [1.0.0] — 2026-08-23

First public release.

The calibration sequence, the formulas and the scales are not new — they were
worked out against real prints over many spools. What is new is that the tool
can now be used by somebody who is not its author: nothing is hard-coded to one
machine, nothing personal ships with it, and setup is a wizard rather than a
file to edit.

### Added

- **Setup wizard** (`Setup.cmd`). Finds the OrcaSlicer installation, reads its
  version, locates the Elegoo system profiles, enumerates every Orca account
  folder, lets you pick among several printer presets, picks up `print_host` if
  you already configured one, and checks it can actually write. Nothing is
  written to OrcaSlicer during setup.
- **Live OrcaSlicer workflow.** Five tests start directly from OrcaSlicer's
  Calibration menu; the project-owned shrinkage bar is included. The legacy
  `Prepare-Templates.cmd` launcher now only explains this safe workflow.
- **`Dry-Run.cmd`** — walk the entire dialog and write nothing at all.
- **`Doctor.cmd`** — read-only diagnosis of the environment.
- **`About.cmd`** — project links, and a way to support the author. The browser
  is opened only after an explicit yes.
- **Preset backups.** Every replaced preset is copied to `preset-backups\` with
  a timestamp before it is overwritten.
- **A once-a-month support note**, shown after a preset is saved successfully,
  and at no other time.

### Changed

- **User data moved to `%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\`.** The
  journal, per-spool measurements and preset backups all
  live outside the program folder, so an update cannot touch them. The original
  wrote them beside the scripts.
- **Saved Orca wizard projects are never reopened.** Their calibration mode is
  session-only. Only the project's own bare shrinkage model opens from disk.
- **Preset writes are atomic**, validated as JSON first, and confirmed by you
  with the exact path shown.
- **OrcaSlicer is asked to close, never forced.** If it does not exit within the
  timeout the program stops and asks, rather than proceeding with the state
  uncertain. The original used the same polite `taskkill`; what is new is
  refusing to continue afterwards.
- **Spool names are normalised through an allow-list** before they reach a path,
  with `..`, separators, drive letters and Windows device names refused.
- **The scales file and the code use English identifiers.** The user-facing
  prose stays Russian. The conversion was checked by running 22 000 randomised
  inputs through the old and new formulas and comparing every result.

### Fixed

- OrcaSlicer's five built-in tests now start from the live Calibration menu.
  Saved wizard projects are rejected because reopening an ordinary 3MF silently
  loses the temperature, pressure-advance, speed or retraction calibration mode.
  The project-owned shrinkage bar remains included and opens automatically.

### Security

- Nothing this project ships contains a printer address. `tools/check_public_safety.py`
  opens every `.3mf` — they are ZIP archives — and fails the build if one does.
- No telemetry of any kind.

[Unreleased]: https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/releases/tag/v1.0.0
