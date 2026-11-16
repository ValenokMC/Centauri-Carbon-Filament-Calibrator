# Contributing

## What fits

- **Corrected scales.** If a tower on your printer does not match
  `plugin/шкалы.json`, a corrected scale with a note on how you verified it is the
  most useful contribution here.
- **A material nobody has calibrated yet** — base profile, drying recommendation,
  test scales.
- **Reports from other printers and nozzles**: which profile, whether the plates
  sliced and printed as expected, what you measured.
- Bug fixes, with a test that fails before and passes after.

## What probably does not fit

- **Anything that sends commands to a printer** from the tab. Orca does that.
- **Telemetry.** No.

## Before you open a pull request

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install trimesh numpy shapely mapbox-earcut DracoPy scipy
python -m pytest
python tools/check_public_safety.py
python tools/build_release.py --version 0.0.0-dev
```

CI runs the same commands. **The safety scanner is not optional**: it looks for
printer addresses, private paths and secrets, including inside `.3mf` and `.zip`
files. If it flags your change it is usually right.

## Changing a scale or a formula

A wrong number there does not crash — it produces a preset that quietly ruins
prints.

- Add a test with a value you measured on a real print, not one recomputed from
  the implementation.
- **Do not widen bounds to make a value fit.** The bounds catch a caliper reading
  off by a factor of ten.
- Say in the pull request how you verified it: material, printer, nozzle.

## House rules

- The plugin ships as **one file**: `plugin/build.py` inlines the page, the scales
  and the helper modules into `kalibrovka.py`. Keep the `# @@…@@` build markers.
- Data stays inside Orca's folder — every file outside it costs the user a
  permission prompt.
- **Tests must not touch a real OrcaSlicer installation or the user's data.**
- **Comments explain why.** Many odd-looking decisions record what went wrong last time.
- **The interface is Russian for now**; code identifiers in the Orca layer and the
  repository documentation are English.

## Commits

```
scales: correct the PETG retraction table against a measured tower
```

not "fix scales". If you measured something to justify it, say what.
