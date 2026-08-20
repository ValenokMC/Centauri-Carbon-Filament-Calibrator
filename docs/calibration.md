# The calibration, test by test

Six plates, in order. The order is not a suggestion: flow is measured at the
final temperature, pressure advance at the final flow, and max flow at the final
pressure advance. Running them out of order produces numbers that describe a
filament nobody has.

The program prepares each plate with the values found so far, so as long as you
follow the menu, this happens by itself.

**Before you start:** dry the filament. The program prints the recommended
temperature and time for the material when you begin. A wet spool produces
measurements that describe the water, not the plastic, and you will do the whole
thing again.

---

## 1. Temperature

**What it prints:** a tower, ten millimetres per block, each block five degrees
cooler than the one below.

**What you measure:** nothing, with a caliper. You look.

Let it cool completely, then examine the bridges, the overhangs, and the
stringing on the transitions. Snap it if you like — the block that has not
started delaminating tells you a lot.

**Judge by the middle of a block, not its edge.** At a boundary the hot end is
still travelling between temperatures, and the top of one block is partly
printed at the temperature of the next.

**What you type:** the temperature printed on the best block.

**Sets:** `nozzle_temperature`, `nozzle_temperature_initial_layer`.

---

## 2. Flow

**What it prints:** OrcaSlicer's flow test — a grid of tiles, each printed at a
slightly different flow ratio, labelled with the offset from the base.

**What you measure:** again, you look. Pick the tile with the flattest top
surface: no gaps between the extrusions, no ridges from too much material.

Low, raking light helps enormously. So does running a fingernail across it.

**What you type:** the *label on the tile*, between about -0.05 and 0.05. Not
the resulting ratio.

This is a common mistake, and the program catches it: entering a ratio like 0.98
here would give a total near 1.96, which it refuses with an explanation.

**Sets:** `filament_flow_ratio`.

> **Why not measure a wall with a caliper?** That method exists in the code
> (`formulas.flow`) and works, but the caliper's jaw pressure alone can shift a
> thin-wall reading by 5 % of flow. The visual test is steadier.

---

## 2b. Shrinkage

**What it prints:** a 100 × 10 × 3 mm bar. This is the plate this project
generates itself.

**What you measure:** the length, with a caliper, after it has cooled to room
temperature. Not while it is warm.

**What you type:** the measured length in millimetres.

100 % means the part came out exactly at nominal. Above 100 % means the plastic
shrank and the slicer will compensate by inflating the model.

The program refuses anything outside 97–103 %. Outside that range it is almost
never the plastic — it is a missed axis calibration, or the wrong face measured.

**Sets:** `filament_shrink`.

---

## 3. Pressure advance

**What it prints:** OrcaSlicer's PA pattern — numbered lines, each printed with
a different pressure advance value.

**What you measure:** which line has the cleanest corners. Too little PA bulges
at a corner; too much leaves a gap just after it.

**What you type:** the line number, counting from zero as printed.

**Sets:** `pressure_advance`, and enables `enable_pressure_advance`.

---

## 4. Maximum volumetric flow

**What it prints:** a tower in vase mode, printing faster as it rises.

**What you measure:** the height, in millimetres, at which under-extrusion
starts — where the wall goes thin, matte, or gappy.

**What you type:** that height.

The program converts it to mm³/s and then takes a safety margin off the result,
because the height where it *starts* failing is already too fast.

There is a ceiling in the scale, and it matters: the tower stops accelerating
once it reaches the cap, so a purely linear formula over-reports. On PLA at
42 mm the naive calculation gave 26 mm³/s where the last two millimetres
actually ran at 25. If the tower survives to the top, the honest answer is "at
least the cap".

**Sets:** `filament_max_volumetric_speed`.

---

## 5. Retraction

**What it prints:** OrcaSlicer's retraction tower — blocks with thin connecting
travel moves that show stringing.

**What you measure:** the height of the cleanest block, in millimetres.

**What you type:** that height.

The steps on this tower are uneven — the bottom block is 1.4 mm, the next 0.8,
then one millimetre each — so it is resolved through a table rather than a
formula. The table was taken from the `Calib_Retraction_tower` markers in the
wizard's own G-code and checked against the actual retraction values.

**Sets:** `filament_retraction_length`.

---

## When a measurement is refused

Every formula has bounds, and a refusal says which mistake is likely:

> flow came out at 0.412, which is far outside anything sensible. Check that you
> measured the wall and not the whole part.

The bounds are not there to be pedantic. A caliper reading off by a factor of
ten produces a plausible-looking number, and a preset built on it quietly ruins
every print made afterwards. Being told now is much cheaper.

If you are convinced the measurement is right and the bound is wrong, the scales
live in `scales.json` and can be edited. Say so in an issue too — a bound that
rejects a real result is a bug worth knowing about.

## Stopping and coming back

Choose **"Выйти"** at any point. Everything is saved in

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\spools\<date> <spool>\measurements.json
```

Start the program again, pick the same spool, and the menu shows what is done
and what is not. The preset already reflects everything measured so far — it is
rewritten after every accepted measurement, not at the end.

## After you finish

OrcaSlicer reads presets **at start-up**. Restart it to see the new one.

If it does not appear, the usual cause is that it was written to one account
folder while Orca is reading another. The program writes to all of them, so this
should not happen — but `Doctor.cmd` lists exactly which folders it found.
