# Licensing

Settled 2026-08-18. See [ADR 0006](docs/decisions/0006-licensing-is-open.md) for
how it was reached and for the audit of every input.

| What | Licence | Text |
| --- | --- | --- |
| **The hardware** — schematics, PCB, footprints, artwork | **CERN-OHL-S v2** | [LICENSES/CERN-OHL-S-2.0.txt](LICENSES/CERN-OHL-S-2.0.txt) |
| **The tools** — everything in `tools/` | **GPL-3.0-or-later** | [LICENSES/GPL-3.0-or-later.txt](LICENSES/GPL-3.0-or-later.txt) |

Both are strongly reciprocal, which was the stated direction of travel:
CERN-OHL-S is written for hardware and defines *Complete Source* as the editable
design files, so shipping Gerbers alone does not discharge the obligation.

## Why the files are laid out like this

**`LICENSE`** in the root is the verbatim, unmodified CERN-OHL-S v2 text and
nothing else. That is not housekeeping: GitHub detects a licence by matching a
root file's *content* against a reference text at high similarity, so any
preamble, table or explanation wrapped around it defeats the match. This
document used to *be* `LICENSE.md` and carried the table above — which is why
GitHub reported the repository as `NOASSERTION`, no licence at all, for the
first day it was public.

**This file** carries everything a human needs and a matcher must not see.

**`LICENSES/`** holds the full text of both licences, so the GPL text ships with
the repository instead of being referenced into the void.

**Per-file `SPDX-License-Identifier` headers** are authoritative for anything
that is not hardware. All 22 tools in `tools/` declare `GPL-3.0-or-later`. A
root `LICENSE` naming one licence does **not** relicense them: where a file
states its own licence, that statement governs.

The root file is the *hardware* licence because the hardware is the point of
this repository — the tools exist to produce it. GitHub will show a single
licence and it should be that one.

## What "Complete Source" means here

The editable design files, not fabrication output:

- `hardware/pcb/*.kicad_sch`, `*.kicad_pcb`, `*.kicad_pro`
- `hardware/pcb/caryatid.pretty/` — the three custom footprints
- **`hardware/art/enso-oro.svg`** — the board's silkscreen mark is generated
  *from* this; the 153 polygons in the board file are an output, not a source
- `docs/pins.yaml` and the generators that consume it

Gerbers, drill files and the `.ses` router output are **not** source.

## Provenance

Every input was audited before this was settled, and nothing blocks reciprocal
licensing. The one item that needed an answer was the ensō, which is
first-party — see [hardware/art/README.md](hardware/art/README.md). Stock KiCad
footprints carry the library exception permitting use in designs; the Newstroke
font behind every silkscreen label is permissive; the custom footprints are ours
from TI land pattern 4222419/E; values and topology are drawn from datasheets
rather than derived from anyone's schematic.

## On the board

Both `CERN-OHL-S v2` and `github.com/ideocentric/caryatid` are printed on the
front silkscreen beside the mark.

The URL was added once the repository was made public (2026-08-18). Until then
the notice deliberately carried no URL, on the grounds that a pointer to
something which does not resolve is worse than none — and adding one is a board
change, so it had to happen before a fabrication run rather than after. It did:
no boards have been fabricated, and the URL is in the current design.
