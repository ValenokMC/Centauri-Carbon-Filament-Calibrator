# Calibration models and Orca's live wizard

There is nothing to download, build or import before calibrating.

## The safe rule

Temperature, flow, pressure advance, maximum volumetric flow and retraction
must be started from OrcaSlicer's **Calibration** menu during the current run.
Slice and print without closing that wizard project.

Do **not** save a generated tower and reopen it later as a reusable template.
An ordinary Orca 3MF keeps the geometry and project settings, but not the
active calibration parameters. The failure is silent: for example, a reopened
temperature tower can slice entirely at its starting temperature instead of
changing by block.

The calibrator therefore refuses to resolve or import these saved filenames:

| Test | OrcaSlicer 2.4.2 menu |
|---|---|
| Temperature | Calibration → Temperature |
| Flow | Calibration → Flow ratio → Flow Dynamics Calibration (YOLO, step 0.01) |
| Pressure advance | Calibration → PA coefficient → Pattern |
| Maximum flow | Calibration → Max volumetric flow |
| Retraction | Calibration → Retraction |

The Russian Orca interface uses the equivalent labels shown by the program.

## One test, start to finish

1. Start `Калибровать.cmd` and choose the spool and test.
2. Read the range and step printed by the calibrator.
3. Start that test from Orca's live Calibration menu.
4. Select the current preset for this spool. For the first temperature test,
   select the configured base preset.
5. Enter the displayed range and step, then let Orca create and slice the test.
6. Print from that live session. Do not save and reopen the generated project.
7. Inspect or measure the print and enter the result in the calibrator.
8. Confirm the preset write. Restart Orca and select the updated spool preset
   before the next test.

For flow, use OrcaSlicer 2.4.2's recommended **YOLO, step 0.01** mode. Its tile
labels match the calibrator's -0.05 to +0.05 offset formula.

## The shrinkage bar

Shrinkage is different. `templates/<material>/2b_shrinkage.3mf` is a bare
100 × 10 × 3 mm bar generated vertex by vertex by this project. It carries no
Orca machine configuration, printer address, account name or personal preset.
The same safe geometry is supplied for every supported material.

The calibrator opens this model automatically. Select the updated spool preset
in Orca before slicing.

## Why the other models are not shipped

The five dynamic models are OrcaSlicer's own calibration assets. This project
does not redistribute them separately. Running them from Orca's menu both
respects that boundary and, crucially, preserves the live calibration mode
required to generate correct G-code.

`Prepare-Templates.cmd` remains in the archive only so an older bookmark or
instruction does not fail. It now explains this workflow and exits; it does not
create, copy or import any file.

## If you already built templates with an older version

Leave them where they are or delete them at your convenience. The calibrator
ignores saved Orca wizard towers and never opens them. Measurements, journal
rows, preset backups and calibrated presets are unaffected.
