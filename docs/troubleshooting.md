# Troubleshooting

**Start with `Doctor.cmd`.** It is read-only — it changes nothing, closes
nothing, opens nothing — and it prints everything the program can see. Most of
what follows is a reading of its output.

---

## `Python not found`

The launcher tried `py -3`, then `python`, then `python3`.

- Python installed without *Add python.exe to PATH*. Re-run the installer,
  choose Modify, tick it.
- Or you have the Microsoft Store stub, which opens the Store instead of
  running. Install from [python.org](https://www.python.org/downloads/).

Check with `py -3 --version` in a terminal.

---

## OrcaSlicer not found

`Doctor.cmd` prints the locations it checked. If yours is elsewhere — a second
drive, a portable install — run `Setup.cmd` and give it the path.

It needs the folder containing `resources\profiles`, which is the OrcaSlicer
install root, not the shortcut and not the executable.

---

## `Базовый профиль «Generic PLA @Elegoo Centauri» не найден`

The Elegoo vendor profiles are not installed in OrcaSlicer.

In Orca: **Preferences → General → Associate/manage vendor profiles**, or add
the Elegoo printer through the printer wizard. `Doctor.cmd` shows how many
filament profiles it can see — zero means none are installed.

---

## The preset does not appear in OrcaSlicer

**OrcaSlicer reads presets at start-up.** Restart it.

The program offers to close Orca before writing for exactly this reason, and
says so at the time.

---

## The preset appears but I cannot select it

A filament preset is only offered for printers it declares compatibility with.
The program builds that list from the system profile plus every user printer
preset that inherits from it.

If you added a printer preset *after* calibrating, the older filament preset
does not know about it. Re-run `Setup.cmd`, then re-run the calibration for that
spool — every measurement is still saved, so it is just a matter of stepping to
the end and letting it rewrite.

---

## The preset was written but to the wrong folder

There is more than one: `user\default\` and `user\<account id>\`. Which one Orca
reads depends on whether you are signed in to an Orca account, and there is no
way to tell from outside — so the program writes to all of them.

`Doctor.cmd` lists the folders it found. If it only found one and Orca is
reading another, you have signed in to an account since setup; re-run
`Setup.cmd`.

---

## A measurement is rejected

Read the message. It says which mistake is likely, and it is usually right:

| Message says | What normally happened |
|---|---|
| flow far outside anything sensible | Measured the whole part instead of a single wall, or typed a ratio where a tile label was wanted |
| shrinkage looks like a missed axis calibration | Measured the wrong face, or measured while the part was still warm |
| height cannot be negative | A typo |
| outside the sensible range for the test | The scale and the plate disagree — see below |

If you are sure the measurement is right, the scales live in `scales.json` and
can be edited. Please also open an issue: a bound that rejects a genuine result
is a bug worth fixing for everybody.

---

## The plate prints with the wrong filament settings

The templates have not been built yet, or not for that material. Run
`Prepare-Templates.cmd`.

Without a template the program still does the arithmetic — it just tells you
which test to run from Orca's own menu instead of opening a prepared plate.

---

## Orca will not close when the program asks

That is by design. `taskkill` is used **without** `/F`, so Orca decides what to
prompt about. If it is asking whether to save a project, it stays open.

Save or discard the project yourself, close Orca, and answer the prompt. The
program will not force it, and it will not proceed with the state uncertain.

---

## I lost a preset by overwriting it

Look in:

```
%LOCALAPPDATA%\CentauriCarbonFilamentCalibrator\preset-backups\
```

Every replaced preset is copied there first, with a timestamp. Copy the one you
want back into the Orca filament folder and restart Orca.

---

## The journal shows six rows for one spool

It should show one. The row key is the date plus the spool name, and each
accepted measurement updates that row rather than appending.

Six rows means the spool name changed between measurements — usually a
different amount of whitespace, or a different case. Spool names are normalised,
but they are still compared exactly.

---

## Everything works but the numbers look wrong

Two things are worth ruling out before anything else:

1. **Was the filament dry?** A wet spool produces measurements that describe the
   water. The program prints the recommended drying temperature and time when
   you start.
2. **Did you run the plates in order?** Flow must be measured at the final
   temperature, PA at the final flow, max flow at the final PA. "Пройти все
   плиты по порядку" does this for you.

---

## Still stuck

1. Run `Doctor.cmd` and copy its output.
2. Open an [issue](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/issues)
   with the bug form filled in.
3. Say which test, which material, what you measured and what you expected.

Replace your Windows user name with `USER` in any path you paste. And **do not
attach a `.3mf` you have not checked** — a project saved by OrcaSlicer may carry
your printer's network address. See [SUPPORT.md](../SUPPORT.md).
