# One-shot scripts

Scripts that were run **once**, kept for provenance, and must not be run again.

This is the opposite of [`tools/gen_pinmap.py`](../gen_pinmap.py), which is a
real generator: `docs/pinmap.md` is derived from `docs/pins.yaml` every time, and
`--check` fails the build if it drifts. Re-running that is the point.

Nothing in this directory works that way.

| Script | Produced | Status |
| --- | --- | --- |
| `gen_power_sch.py` | `hardware/pcb/power.kicad_sch` | **spent** — the schematic is now edited in KiCad |
| `gen_seed_sch.py` | `hardware/pcb/seed.kicad_sch` | **spent** — same |
| `gen_panelio_sch.py` | `hardware/pcb/panel-io.kicad_sch` | **spent** — same |
| `gen_audio_sch.py` | `hardware/pcb/audio.kicad_sch` | **spent** — same |
| `gen_board_skeleton.py` | `hardware/pcb/caryatid.kicad_pcb` | **spent** — outline only; footprints come from the GUI |
| `symlib.py` | — | read-only helper, safe to import |

## Why keep them at all

Each generator records exactly how its sheet was first captured: which symbol came from which library, where every component sat, and
which net each pin joined. That is why the capture could be checked by exporting
the netlist and diffing it node-by-node against
[`docs/power-sheet.md`](../../docs/power-sheet.md) rather than by reading the
schematic and hoping.

It also documents two things that were only discovered by generating the file:
`power_out` on both of the bq24074's `OUT` pins is an ERC error, and local labels
are sheet-qualified (`/power/SW`, not `SW`) which defeats a bare netclass
pattern.

## Why not run them

**The schematic stopped being derived the moment it existed.** Placement,
wiring, and anything added in KiCad live only in `power.kicad_sch`. Re-running
the generator rewrites that file from the component table in the script and
throws all of it away.

The script refuses to run without `CARYATID_ALLOW_REGEN=1`. That guard is there
to stop an absent-minded `python3 gen_power_sch.py`, not to make regeneration a
supported workflow — it is still destructive with the variable set.

**If the circuit changes:** change it in KiCad, and update
`docs/power-sheet.md`. Do not come back here.