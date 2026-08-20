# Getting help

## Where to go, in order

1. **[Documentation](docs/installation.md)** — installation, the test-by-test
   guide, and troubleshooting.
2. **Run `Doctor.cmd`.** Read-only. It prints everything the program can see
   about your OrcaSlicer installation, and it answers most setup questions on
   its own.
3. **[Discussions](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/discussions)** —
   questions, "is this measurement plausible", results from a spool nobody has
   tried yet.
4. **[Issues](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/issues)** —
   a reproducible bug or a specific request.
5. **[@SupporBiBot](https://t.me/SupporBiBot?start=centauri_calibrator)** — if
   you do not have a GitHub account, or would rather not write in public.

## What to expect

One person, in their own time. An answer can take a few days.

A report saying which test, which material, what you measured and what you
expected gets a useful answer. "The number is wrong" cannot be acted on — every
formula here has been checked against real prints, so a wrong number is usually
a wrong measurement, a wrong scale, or a genuinely interesting bug, and only the
details tell those apart.

## What to send

- Application version, from `Doctor.cmd`
- Windows version
- OrcaSlicer version
- Printer model and nozzle size
- Material and which test number
- What you measured, what the program computed, what you expected
- The relevant part of the console output

## What NOT to send

> [!CAUTION]
> **A `.3mf` you saved yourself may contain your printer's network address.**
> OrcaSlicer stores `print_host` inside the project file. If you attach a plate
> you saved, you may be publishing your internal IP.

- ❌ **A `.3mf` you have not checked.** If you need to send one, run
  `Prepare-Templates.cmd` first — the copy it stores is sanitised — or open the
  file as a ZIP and look at `Metadata/project_settings.config`.
- ❌ **Your `Journal.csv`.** It is a record of every spool you own, with dates.
  Send the one row that matters, not the file.
- ❌ **Your OrcaSlicer profile folder.** It contains your printer's address and
  your account id.
- ❌ Screenshots with your printer's IP address or your Orca account name
  visible.

The console output is safe. It shows paths inside your own user folder, so
replace your user name with `USER` if you would rather not publish it.

## If you already published your printer's address

It is an address on your own LAN, so the exposure is limited — but it does tell
people how your network is laid out.

- Delete or edit the post.
- If your printer's ports are reachable from outside your network, close them
  now. SDCP has no authentication; see [docs/security.md](docs/security.md).

## Security problems

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
