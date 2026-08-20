# Contributing

## What fits

- **Corrected scales.** If a tower on your printer does not match what
  `scales.json` says, a corrected scale with a note on how you verified it is
  the single most useful contribution here.
- **A material nobody has calibrated yet**, with its base profile, drying
  recommendation and test scales.
- Bug fixes, with a test that fails before and passes after.
- Documentation, especially [docs/calibration.md](docs/calibration.md) — it is
  the page people read while standing at the printer.

## What probably does not fit

- **Support for another nozzle size or another printer.** The plates are built
  for a 0.4 nozzle on a Centauri Carbon. Claiming more without hardware to test
  on would mean somebody spends two days printing to get a number that describes
  nothing.
- **A third-party dependency.** Having none is a feature.
- **Automating the slicing or the sending.** OrcaSlicer does that. Wrapping it
  means owning its behaviour across versions.
- **Anything that forces OrcaSlicer to close**, or continues while its state is
  unknown. A `taskkill /F` throws away somebody's unsaved project.
- **Telemetry.** No.

## Before you open a pull request

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
python tools/check_public_safety.py
```

Both must pass. CI runs the same two commands.

**The safety scanner is not optional.** It opens every `.3mf` in the repository —
they are ZIP archives — and fails if one carries a printer address, and it looks
for private paths and secrets in everything else. If it flags your change it is
usually right.

## Changing a formula

`formulas.py` is the file where a mistake is most expensive: a wrong number
there does not crash, it produces a preset that quietly ruins prints.

- Add a test with a value you measured on a real print, not one recomputed from
  the implementation. A test that recomputes only proves the code equals itself.
- **Do not widen the bounds to make a value fit.** The bounds catch a caliper
  reading off by a factor of ten. If a bound rejects a genuine result, say so —
  that is a real bug and worth its own issue.
- Say in the pull request how you verified it.

## Changing anything that writes

`presets.py`, `plates.py` and `journal.py` write files a user cannot easily
reconstruct. Preserve, and keep the tests for:

- back up before replacing
- validate before touching the filesystem
- write to a temporary file, then `os.replace`
- on failure, leave the original byte-for-byte unchanged

## House rules

- **Standard library only** in `src/`.
- **Tests must not touch a real OrcaSlicer, a real journal, or a running
  slicer.** The autouse fixtures make each of those an error. If your change
  breaks one, the change is wrong.
- **A template is opened read-only.** Always. `tests/test_safety.py` asserts its
  hash is unchanged after personalisation.
- **Comments explain why.** Most of the odd-looking decisions here have a
  comment recording what went wrong last time, and that comment is the reason
  the odd-looking decision is correct.
- **Interface strings are Russian, everything else is English.**

## Commits

```
scales: correct the PETG retraction table against a measured tower
```

not "fix scales". If you measured something to justify it, say what.
