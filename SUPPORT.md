# Getting help

## Where to go, in order

1. **[README](README.md)** — install, what each test measures, where data lives.
   The working plan and known gaps are in [plugin/СОСТОЯНИЕ.md](plugin/СОСТОЯНИЕ.md).
2. **The tab's own "Диагностика" section** (bottom of the Filament Lab tab). It
   shows the paths the plugin uses and the last errors — paste it into a report.
3. **[Discussions](https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin/discussions)** —
   questions, "is this measurement plausible", results from a new spool.
4. **[Issues](https://github.com/ValenokMC/OrcaSlicer-Calibration-Plugin/issues)** —
   a reproducible bug or a specific request.
5. **[@SupporBiBot](https://t.me/SupporBiBot?start=centauri_calibrator)** — if you
   have no GitHub account or would rather not write in public.

One person, in their own time. An answer can take a few days.

## What to send

- Plugin version (Orca → Plugins) and OrcaSlicer version
- Printer profile and nozzle size
- Material and which test
- What you measured, what the tab computed, what you expected
- The "Диагностика" text

## What NOT to send

> [!CAUTION]
> **A `.3mf` you saved yourself may contain your printer's network address.**
> OrcaSlicer stores `print_host` inside project files. Plates written by the tab
> do not include printer settings, but a project you saved from Orca afterwards may.

- ❌ A `.3mf` you have not checked — open it as a ZIP and look at
  `Metadata/project_settings.config` first.
- ❌ Your whole `Журнал.csv` — send the one row that matters.
- ❌ Your OrcaSlicer profile folder — it contains your printer's address and account id.
- ❌ Screenshots with your printer's IP address or your Orca account name visible.

## Security problems

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
