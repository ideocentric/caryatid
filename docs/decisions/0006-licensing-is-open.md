# 0006 — Licensing is open, and must be settled before publication

- **Status**: **Partly settled.** Derivation answered; licence still open.
- **Date**: 2026-08-08
- **Amended**: 2026-08-08 — the derivation question below is now decided.

## Decided: draw from the datasheets

**The schematic is drawn independently from the TI application circuits for the
bq24074 and TPS61023. It does not derive from Adafruit's schematics.**

References in the platform spec to "per Adafruit reference" and "Adafruit-style
headroom" are to be read as *design guidance about values and topology* — the
same application notes anyone would read — not as permission to copy a source
file. Nobody may open an Adafruit schematic and trace from it.

This is the decision that expires, and it is now taken in the direction that
keeps every option open. **Every licence remains available, including
permissive.**

## Still open: which licence

Direction of travel: **as strongly copyleft as the licence family allows.**

The relevant candidate is **CERN-OHL-S**, not CC BY-SA. This matters and is easy
to get backwards:

- **CERN-OHL-S** is written for hardware. It defines "Complete Source" — the
  editable design files — so sharing gerbers alone does not discharge the
  obligation. It is the genuinely copyleft choice.
- **CC BY-SA** is a content licence pressed into hardware service. It does *not*
  define what source means for a physical object, which is why loa's own ADR
  0006 has to state the intent in prose and acknowledge the gap. Weaker in
  exactly the way that matters here.

loa's hardware is provisionally CC BY-SA because it was modelled on Adafruit's
CC BY-SA PowerBoost. **This board carries no such inheritance now**, so it is
free to take the stronger licence.

Remaining to decide before publication:

1. **CERN-OHL-S version** — 2.0 is current.
2. **Whether the instruments follow.** loa's provisional CC BY-SA was chosen
   under a constraint that no longer applies to this board and may no longer
   apply to loa either.
3. **Firmware and tooling**, if any lands here, is a separate question — GPL is
   the natural pair.

## Until then

The repository is **private**, with no licence file: default copyright, all
rights reserved. That is honest while the borrowing question is being worked
through, and it is the correct state for a repository that is not yet public.


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