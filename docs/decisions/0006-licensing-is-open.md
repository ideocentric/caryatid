# 0006 — Licensing is open, and must be settled before publication

- **Status**: **Open.** Nothing here is decided.
- **Date**: 2026-08-08

## Context

This repository has **no licence file**, which means default copyright: all
rights reserved. That is honest while undecided and unacceptable once shared.

The decision is not inherited from the instruments. loa's hardware is
provisionally CC BY-SA 4.0 (its ADR 0006), but [0002](0002-one-board-many-instruments.md)
separates this board precisely so it is not bound by any one instrument's
choice.

The question turns on one thing:

**Is the schematic derived from Adafruit's, or drawn from the TI datasheets?**

The spec describes the charger as bq24074 "per Adafruit reference" and the boost
as TPS61023 with "Adafruit-style headroom". If that means deriving from
Adafruit's published schematics, those are CC BY-SA and the derivative must be
too. If it means reading the same TI application circuits they did and drawing
independently, every licence stays available — including permissive.

This is cheap now and expensive to reverse once a schematic exists. It cannot be
un-derived after the fact.

## The decision to make

1. **Derive, or draw from datasheets?** Deriving is faster and locks CC BY-SA.
2. **Which licence follows.** Permissive maximises reuse, which is the stated
   point of making the board separable at all (loa's P-11).
3. **What counts as source.** If CC BY-SA: it does not define "source" for a
   physical object, so this repository must state it — the editable KiCad
   project, not fabrication output.

## Consequences of leaving it open

The repository stays private. No schematic capture that copies from an Adafruit
source file should begin until item 1 is answered, because that answer stops
being available the moment it does.