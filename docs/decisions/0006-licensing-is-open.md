# 0006 — Licensing is open, and must be settled before publication

- **Status**: **Settled 2026-08-18.** CERN-OHL-S v2 for the hardware, GPL-3.0-or-later for the tools. Derivation was answered 2026-08-08.
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
## Amended 2026-08-18 — the inputs are audited, and nothing blocks copyleft

Prompted by putting the ensō on the silkscreen: *does anything we have borrowed
prevent a copyleft licence?* Every input to the design was enumerated. **None
blocks it.**

| Input | Terms | Blocks? |
| --- | --- | --- |
| `hardware/art/enso-oro.svg` | **first party** — drawn in Illustrator by the author, the house mark across the instrument projects | no |
| ~120 stock KiCad footprints | CC-BY-SA 4.0 **with the library exception** for use in designs | no |
| KiCad Newstroke font — every silk label and the wordmark | permissive / public-domain lineage | no |
| 3 custom footprints (BQ24074RGT, both Seed sockets) | ours, drawn from TI land pattern 4222419/E | no |
| Values and topology | drawn from datasheets — the decision above | no |
| Daisy Seed documentation | MIT | no |
| `svgelements`, Freerouting, `kicad-cli` | tools; their output is not a derivative of them | no |

**The artwork was the only item in real doubt, and only because the file cannot
answer for itself** — the Illustrator export carries no metadata, no author, no
licence and no download record. Had it come from a stock library, most such
licences forbid redistributing the asset in editable form, and a `.kicad_pcb`
holding 12 255 points of its outline is exactly that. It is first party, so the
question closes. Provenance is now recorded in
[hardware/art/README.md](../../hardware/art/README.md) so nobody has to ask again.

**Two items remain to settle, both narrower than the original question:**

1. **Which licence.** Unchanged, and the direction of travel is unchanged:
   CERN-OHL-S for the hardware, GPL for the tools.
2. **The tools already assert one.** Every file in `tools/` carries
   `SPDX-License-Identifier: GPL-3.0-or-later`, which matches that intent but
   asserts a decision this ADR still records as open, and there is no LICENSE
   file in the repository. **Either ratify the split or correct the headers** —
   they should not be the only place the licence is stated.

**If CERN-OHL-S is adopted**, note two consequences that touch work already
done. It defines Complete Source as the editable design files, which is why the
SVG is committed rather than left in gitignored `local/`. And it wants a notice
on the product — `tools/branding.py` deliberately prints no licence line, and
adding one is a board change, so it must happen *before* a fab run, not after.


## Settled 2026-08-18 — CERN-OHL-S v2 and GPL-3.0-or-later

**Hardware: CERN-OHL-S v2. Tools: GPL-3.0-or-later.** Both strongly reciprocal,
which is the direction this ADR recorded from the start. Texts are in
`LICENSES/`; the split and what counts as Complete Source are in
[LICENSE.md](../../LICENSE.md).

This closes the two items the amendment above left open:

1. **Which licence** — answered.
2. **The tools already asserted one.** Every file in `tools/` carried
   `SPDX-License-Identifier: GPL-3.0-or-later` while this ADR still said the
   licence was open. Those headers are now **ratified rather than corrected** —
   they turned out to state the right answer, but they stated it before it was
   taken, which is the wrong order and worth not repeating.

**Consequences now live:**

- **`hardware/art/enso-oro.svg` had to be committed**, and was. CERN-OHL-S
  defines Complete Source as the editable design files; a repository whose logo
  existed only as 153 flattened polygons would not have met it.
- **The board carries a notice.** `CERN-OHL-S v2` is on the front silkscreen
  beside the mark, at 1 mm.
- ~~No source URL on the board, because the repository is private.~~
  **Done 2026-08-18.** The repository is **public** at
  <https://github.com/ideocentric/caryatid>, and the board carries
  `github.com/ideocentric/caryatid` on the front silkscreen at (178, 116). The
  bare domain form, because `https://` inks 30.63 mm and does not fit anywhere
  useful; the URL was verified to resolve by anonymous clone before this was
  written.
