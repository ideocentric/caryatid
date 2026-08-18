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

`CERN-OHL-S v2` is printed on the front silkscreen beside the mark. It is **not
accompanied by a URL**, because the repository is private as of this writing —
a notice pointing at something that does not resolve is worse than none. **If
this design is published, add the source URL to the silkscreen**, which is a
board change and therefore has to happen before a fabrication run, not after.
