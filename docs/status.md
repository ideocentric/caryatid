# Status

Where the board is, and what happens next. Read this first.

## The board is routed

As of `64c25e6`. Every electrical check is at zero:

| | |
| --- | --- |
| real unconnected connections | **0** |
| zone-to-zone unconnected | **0** |
| shorts, clearance, hole clearance | **0** |
| tracks under the 0.20 mm rule | **0** |
| floating ground copper | **0** |
| `tools/check_board.py` | **10/10 pass** |

150 × 90 mm, two layers, 128 footprints, all on the front. Ground pour both
sides, 146 GND vias. Power nets around U1 and U2 are poured from hand-drawn
outlines rather than routed; see [ADR 0008](decisions/0008-board-outline-and-layer-count.md)
and the commit history for why.

Three DRC items remain **deliberately**:

- **3 `silk_overlap`** at 0.21–0.22 mm. Our rule is 0.25; JLC's floor is 0.15.
  They print and read correctly.
- **5 `via_dangling`**. These are junctions where two or three tracks meet, not
  loose ends. Removing this kind wholesale broke two connections once already.
- **5 `lib_footprint_mismatch`**. Metadata only — `Datasheet` and `Description`
  fields KiCad adds on placement, plus reference visibility. No geometry
  differs, so nothing about the fabricated board changes.

## Next, in order

1. ~~**Round the board corners.**~~ **Done** — 3 mm radius, four `gr_line` sides
   and four 90° `gr_arc` corners, pours refilled to follow them. Reasoning and
   what did *not* constrain the radius are in
   [ADR 0008](decisions/0008-board-outline-and-layer-count.md); change it with
   `python3 tools/round_corners.py --radius N --apply`.
2. **Component silkscreen.** D1 has a known fix. 108 of 128 references are
   hidden — residue of "hide the back references" from when every SMD part was
   on the back face. U1, U3, U4, C7 and D1 are now visible; U2, L1 and FB1 stay
   hidden because their labels collide with their own outlines and get clipped
   by solder mask, which puts ink on bare copper.
3. **Human-readable silkscreen at the connectors** — `SW1`, `SW2`, `SW3` and so
   on beside each jack, not just reference designators. This is already a
   requirement: [connectors.md](connectors.md) says to print the function of
   every pin beside every connector, because the board is assembled once and
   cabled differently for each instrument, months apart.

   **absonus did exactly this and the sizes are known**: `SW1`, `SW2`,
   `Audio Out`, `Pressure`, `Position`, `L`, `R`, all **1 × 1 mm at 0.15
   thickness**, F.SilkS, rotated 90°. Note 0.15 is precisely JLC's stroke floor
   and `check_board.py`'s minimum — zero margin, though absonus was fabricated
   with it. Consider 0.16–0.18 here.
4. **Logo and font from absonus**, placed on silkscreen. **Located, and there is
   no artwork to import.** The source is
   `synths/daisy/ribbon-synth/archive/hardware/pcb-v0.1/absonus-v0.1.kicad_pcb`,
   and it contains **zero image objects** — the branding is plain KiCad stroke
   text in the built-in font. No font file, no bitmap, nothing to convert:

   | text | size | thickness | |
   | --- | --- | --- | --- |
   | `absonus` | 3.556 × 2.54 mm | 0.20 | bold |
   | `v0.2` | 1 × 1 mm | 0.15 | |

   Both `(layer "F.SilkS")`, rotated 90°, `(justify left bottom)`.
5. **Manufacturing readiness**, then anything still unticked.

## Known open, beyond that list

From [capture-checklist.md](capture-checklist.md) and [sourcing.md](sourcing.md):

- **Tent the QFN thermal vias.** They sit under paste apertures and MUST be
  mask-plugged, or paste wicks down them during reflow.
- **Extended-part loading fee** on `C5339083`, the cell holder.
- **The J4 bicolour LED is UNVERIFIED** — Amazon `B01CFZMO3I`. The green die
  decides whether it works: J4 hangs on `VOUT`, which falls to ~3.0 V, so an
  InGaN green at 3.0–3.2 V goes dark exactly when the charge indicator matters.
  Test it at 3.0 V, not 4.2. See [sourcing.md](sourcing.md).
- **Parts still to source** — see the table in sourcing.md.
- **Datasheets** are gathered in `local/datasheets/`, gitignored. Index and
  links in [datasheets.md](datasheets.md).

## Working with the board

```
python3 tools/check_board.py        # ten checks KiCad's DRC does not do
python3 tools/cycle.py              # placement -> fully routed, ~10 min
python3 tools/cleanup.py            # duplicate tracks, co-located vias, priorities
python3 tools/pour_from_drawing.py  # convert hand-drawn F.Cu polygons into pours
python3 tools/reset_placement.py    # back up and strip to placement only
python3 tools/round_corners.py      # corner radius on the Edge.Cuts rectangle
```

**Lock any copper you place by hand.** `cycle.py` strips everything unlocked and
re-routes; `export_dsn.py` hands locked copper to Freerouting as `(type protect)`
so it routes around it. Without the lock, hand work is deleted and not
regenerated — `fanout.py` only escapes radially, and routes like SW's channel
exit out of U2 do not come back.

**Reload in KiCad after any tool run** (File → Revert). The tools write to disk
and KiCad will not notice.

## Restore points

Tags, all pushed:

- `snapshot/pours-u2-routing`
- `snapshot/before-via-removal`

Plus timestamped copies in `local/backups/`, which is gitignored.