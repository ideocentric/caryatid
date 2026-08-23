# Findings ledger

> **Before writing anything here, check which checkout you are in.** caryatid is
> developed in its standalone clone; a copy reached through another project's
> submodule directory (`hardware/platform/` in loa) is read-only. See the top of
> the [root README](../README.md).

Measured facts about physical things that the repo cannot check for itself.

One file per finding in `findings/`, keyed by a stable identifier. Each record
carries what was originally *claimed*, what was *measured*, an **append-only**
evidence list with dates, and a `status`. When a fact changes, a new evidence
entry goes on the end and `status` / `last_verified` are updated — history is
never rewritten.

## Why this exists here

caryatid's documents are full of numbers, and most of them are checkable: DRC
reads the board, `check_board.py` reads the board, `verify_parts.py` reads JLC.
A handful are not. The enclosure is a die-cast box on a bench; the only way to
know its interior is to measure it, and the only place that measurement lives is
whatever we write down.

Those numbers had been derived instead — catalogue nominal minus half an inch
per axis, a sparse point cloud out of a STEP file — and then restated across
four documents until they read like measurements. When the box was finally
measured, the derived working rectangle turned out to under-read it by about
14 mm on each axis. Nothing broke, because the error was conservative. It could
as easily have gone the other way.

## The rule

**Facts go in the ledger first. Documents are derived from it, never the
reverse.** If a number in `docs/` needs to change, change the record and
regenerate the prose. A figure in a document that has no record behind it is
unverified, and should say so.

## Records

| record | covers |
| --- | --- |
| [`bud-cu477-interior.yaml`](findings/bud-cu477-interior.yaml) | BUD CU-477 floor, height, plate profile, board mounting datum and the power switch intrusion |
| [`bt1-cell-fit.yaml`](findings/bt1-cell-fit.yaml) | Whether the Orbtronic 3400 mAh protected cell fits the BH-18650-PC holder. `conflict`: it seats, over-deflecting the contacts past their rating |
| [`jlc-bom-sourcing.yaml`](findings/jlc-bom-sourcing.yaml) | The LCSC codes (43 as of 2026-08-23): cost, library split, assembly mode, pre-orders, and the build-quantity decision |
