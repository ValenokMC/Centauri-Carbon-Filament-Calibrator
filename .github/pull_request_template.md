## What this changes

<!-- One or two sentences, from a user's point of view. -->

## Why

<!-- The problem, not the solution. Fixes #123 -->

## How it was tested

<!--
For a formula or a scale change this is the important section. Say what you
printed, what you measured, and how you checked it. A value recomputed from the
implementation proves only that the code equals itself.
-->

- [ ] `python -m pytest tests/ -q` passes
- [ ] `python tools/check_public_safety.py` passes
- [ ] Verified against a real print — material, printer, nozzle:
- [ ] Not applicable (documentation only)

## Checklist

- [ ] No third-party runtime dependency added to `src/`
- [ ] No test touches a real OrcaSlicer install, a real journal, or a running slicer
- [ ] Templates are still opened read-only, and the hash test still passes
- [ ] No `.3mf` added that carries a `print_host`
- [ ] No personal data in the diff — printer address, account name, user paths, real spool names
- [ ] `CHANGELOG.md` updated under `[Unreleased]`, if a user would notice this

## If this touches a formula or a scale

- [ ] I did **not** widen a bound to make a value fit
- [ ] I added a test using a value I measured, not one recomputed from the code
- [ ] I said above how I verified it

## Anything the reviewer should know

<!-- Trade-offs, alternatives rejected, parts you are unsure about. -->
