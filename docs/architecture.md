# Architecture

For someone about to change the code.

## Shape

```
  wizard.py ──┐                      ┌── orca.py ──► OrcaSlicer install (read)
              ├── config.py          │              user profile tree (read)
  session.py ─┤                      │              preset folders     (write)
              ├── scales.py ─► formulas.py   (pure)
              ├── templates.py ─► geometry.py (project-owned shrinkage model)
              ├── plates.py                  (legacy 3MF safety helpers)
              ├── journal.py                 (write: Journal.csv)
              ├── presets.py                 (write: the preset, atomically)
              ├── names.py                   (pure)
              └── support.py                 (pure + one small state file)
```

`console.py` holds every prompt, so they all behave the same way: Enter always
takes the default, and the default is always shown.

## Modules

| Module | Responsibility | Writes anything? |
|---|---|---|
| `paths.py` | Where user data lives | creates directories |
| `config.py` | What setup found, atomic save | `config.json` |
| `console.py` | Prompts and colour | no |
| `formulas.py` | **Pure.** Measurement → value | no |
| `scales.py` | Loads `scales.json`, dispatches to a formula | no |
| `names.py` | **Pure.** Safe filenames, path containment | no |
| `orca.py` | Discovery. Read-only except `request_close` | no |
| `presets.py` | Building and writing the preset | the preset |
| `plates.py` | 3MF inspection/sanitising helpers retained for safety tests | only when called explicitly |
| `geometry.py` | Building the project-owned shrinkage 3MF from vertices | generated models |
| `templates.py` | Route the shrinkage model; reject saved Orca wizard projects | no in the normal workflow |
| `journal.py` | `Journal.csv` | the journal |
| `support.py` | Links, the 30-day rule | `support.json` |
| `session.py` | The calibration dialog | via the above |
| `wizard.py` | First run | `config.json` |

The pure modules — `formulas`, `names`, and most of `scales` — hold the logic
that has to be right, and can be tested by calling a function and looking at
what comes back.

## The formulas

`formulas.py` has no input and no file access on purpose: a formula can be
corrected without touching the dialog, and checked in one line.

Every function has **bounds**, and they are load-bearing rather than defensive.
A caliper reading off by a factor of ten produces a plausible-looking number,
and a preset built on it quietly ruins every print made afterwards. Refusing it
and naming the likely mistake is most of the value.

`continuous()` has a `ceiling` for a reason worth keeping: the max-flow tower
stops accelerating once the ramp hits its cap, so a linear formula over-reports
above that height. On PLA at 42 mm the naive result was 26 mm³/s where the tower
was really running at 25.

These were ported from an earlier Russian-named implementation. The port was
checked by pushing 22 000 randomised inputs through both and comparing every
result and every raised exception.

## The scales file

`scales.json` says what to print, within which limits, and how a measurement
becomes a value. Without those numbers a measurement is meaningless — "12.4 mm"
on its own says nothing.

Structural keys and enum values are English. The prose fields — `question`,
`hint`, `steps`, `after`, `print_via` — are Russian, because the interface is.

`unverified: true` on a test marks a number taken from typical values rather
than measured on this printer. The dialog warns when it shows such a test.

## Live wizard tests and the shrinkage model

Orca's five dynamic calibration modes are session state, not ordinary 3MF
project settings. Saving and reopening their geometry silently loses the
temperature/PA/speed/retraction behaviour. `Session.prepare_plate()` therefore
returns `None` for every filename in `templates.FROM_WIZARD`, and
`templates.import_from_wizard()` rejects them.

The only file automatically opened is the project-owned bare shrinkage bar.
It is safe to reuse because it has no dynamic calibration mode and carries no
machine, network or personal preset data. Tests cover both halves of this rule:
saved wizard projects never open, while shipped shrinkage geometry does.

`plates.py` still contains the old generic inspection, sanitising and
personalisation primitives. They are useful for archive safety tests and
backward compatibility, but they are not part of the public calibration flow.
See [templates.md](templates.md) and `THIRD_PARTY_NOTICES.md`.

## Writing the preset

The one dangerous operation, so it is layered:

1. `plan()` reports create-versus-replace, and the dialog shows it.
2. `back_up()` copies the existing file to `preset-backups\` with a timestamp.
3. The preset is serialised and **re-parsed before the filesystem is touched** —
   an unserialisable value fails here, not half way through replacing a working
   file.
4. Written to a temporary file in the same directory, then `os.replace`, which
   is atomic on Windows.
5. On any failure the original is still there.

A corrupt filament preset stops OrcaSlicer from starting, which is why this is
not a plain `open(path, "w")`.

It writes to **every** account folder, because which one Orca reads depends on
whether the user is signed in and there is no way to tell from outside.

## The same-name trap

`orca.collect_system_filaments()` is restricted to named vendors, in priority
order. Profile names in Orca's tree are not unique: `fdm_filament_pla` exists in
three dozen vendor folders with different flow ratios — 0.98, 0.95, 1, 0.92.

Scanning everything makes it trivial to pick up somebody else's. That is how the
ratio for `Generic PLA @Elegoo Centauri` once resolved to 1.0 instead of 0.98,
which would have thrown every flow calibration off by 2 %. There is a test for
it with a fixture containing exactly that collision.

## Testing rules

Three fixtures enforce what the suite must never do:

- **`isolated_data_dir`** (autouse) redirects `paths.data_dir()` to a temporary
  directory, so no test can write to a real journal.
- **`never_touch_real_orca`** (autouse) replaces `orca.request_close` and
  `orca.open_file` with functions that raise. A test that would close a running
  slicer fails instead.
- **`fake_orca`** builds a complete profile tree in a temporary directory,
  including the duplicate-name collision above and a machine preset with an
  invented address.

If a change breaks one of those, the change is wrong.

## Things deliberately not done

- **No GUI.** The dialog is a numbered menu because calibration is a two-day
  process interrupted by prints, and a console session is trivially resumable.
- **No automatic slicing or sending.** OrcaSlicer does that; wrapping it would
  mean owning its behaviour.
- **No guessing when Orca is in an unknown state.** If the slicer will not close,
  the program stops rather than continuing.
