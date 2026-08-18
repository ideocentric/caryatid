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

**A plain `kicad-cli pcb drc` run now reports zero.** One kind of item remains,
excluded in KiCad with its reason recorded in `tools/drc_exclusions.py`:

- ~~2 `silk_overlap`~~ **Both fixed rather than accepted.** J11's reference
  nudged clear; BT1's `+` marker moved from local x −4.5 to −5.5, giving
  0.448 mm. There is no `silk_overlap` anywhere on the board.
- ~~5 `via_dangling`~~ **Removed.** They were called "junctions where two or
  three tracks meet, not loose ends" here, which was true and beside the point.
  Two or three tracks did meet at each — **on F.Cu, with nothing whatever on
  B.Cu**. B.Cu carries only the ground pour, so a `+5V` or `RGB_B` via reaching
  it had nothing to land on, and since the pour must clear around each one they
  were punching holes in the ground plane for no purpose. The F.Cu tracks meet
  at a coincident point and stay connected without them.

  This was **not** the earlier cascade, where deleting a via orphaned the track
  feeding it. Only the vias went; no track was touched. Verified on a copy
  before applying — real unconnected stayed 0 and no `track_dangling` appeared.
- **5 `lib_footprint_mismatch`**. Metadata only — `Datasheet` and `Description`
  fields KiCad adds on placement, plus reference visibility. No geometry
  differs, so nothing about the fabricated board changes.

## Next, in order

1. ~~**Round the board corners.**~~ **Done** — 3 mm radius, four `gr_line` sides
   and four 90° `gr_arc` corners, pours refilled to follow them. Reasoning and
   what did *not* constrain the radius are in
   [ADR 0008](decisions/0008-board-outline-and-layer-count.md); change it with
   `python3 tools/round_corners.py --radius N --apply`.
2. **Component silkscreen.** **D1 and U1 are done** — D1's reference moved from
   below the body to above it, `-2.5` to `+2.5`, the exact mirror; U1's went
   `0` to `0.2875` on X. Both clear the 0.25 mm rule outright.

   Still open: **106 of 128 references are hidden** — residue of "hide the back
   references" from when every SMD part was on the back face, which no longer
   describes the board. U1, U3, U4, C7 and D1 are visible; U2, L1 and FB1 stay
   hidden deliberately, because their labels collide with their own outlines and
   get clipped by solder mask, which puts ink on bare copper. The rest is a
   decision nobody has made rather than one that was made — worth taking as its
   own sweep, not part by part.
3. ~~**Human-readable silkscreen at the connectors.**~~ **Done** — all **77
   connector pins** are labelled, by `tools/pin_labels.py`. 61 at the full
   1 × 1 mm absonus size, 5 at 0.9, 4 at 0.85, 7 at 0.8; zero DRC issues.
   Re-run the tool after any placement change — the labels are board-level
   `gr_text` and do **not** follow a connector that moves.

   **All 77 are locked.** A hand-moved label keeps the uuid the tool gave it,
   so without a lock the next `--apply` silently reverts it. `--apply` is now a
   byte-for-byte no-op; `--relock --apply` is the deliberate override.

   Pin pitch decided the design. At 2.50 mm with 0.25 mm clearance, one row of
   1 mm text fits **two characters** — not enough for `3V3`. Staggering
   alternate pins into two rows doubles the effective pitch and buys five.

   **Seven connector references moved** to make room: J6, J7, J8, J9, J10, J13B
   and J15 sat directly above their connectors, in the only band the labels
   could use. They are now rotated 90° in the gap beside each connector.
4. ~~**Logo and font from absonus**~~ **Done.** `caryatid` + `v0.1` on
   F.SilkS at the bottom right, by `tools/branding.py`. absonus's exact style —
   3.556 × 2.54 mm, thickness 0.20, bold — but **not** its 90° rotation, which
   was a placement decision for a tall board. There was no artwork to import:
   absonus's branding is plain KiCad stroke text and that board holds zero
   image objects.

   **`v0.1` is an inference.** The repo has no version tag, no title block and
   no version in the docs; it is the obvious label for a first spin, recorded
   in the tool so nobody later reads it as sourced.

   **No licence line, deliberately.** [ADR 0006](decisions/0006-licensing-is-open.md)
   still reads *"licence still open"* and there is no LICENSE file. Silkscreen
   is permanent; a notice would settle by accident a decision not yet taken.

   The block sits 2 mm left of the clear area's centre. Centred, `v0.1` landed
   where the M3 screw head goes at (195,115) — a Ø6 head or any washer would
   hide the revision marking. **Nothing in DRC models a screw head**; it was
   caught by rendering the silkscreen and looking at it.


5. **Manufacturing readiness**, then anything still unticked.

## Known open, beyond that list

From [capture-checklist.md](capture-checklist.md) and [sourcing.md](sourcing.md):

- ~~Tent the QFN thermal vias.~~ **Done, and it needed a redesign rather than a
  tent.** All four barrels were OPEN on the top face — the vias declare
  `(layers "*.Cu")` and open no mask themselves, but the EP pad declares
  `F.Mask` across the whole 1.68 mm square and the vias sit inside it. Open on
  top, sealed at the bottom, paste printed over the hole: a blind cavity that
  wicks paste in and traps expanding gas. Now **two** vias, mask-tented on both
  faces, with the EP mask opening moved clear of them. `tools/fix_ep_thermal.py`.
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
python3 tools/pin_labels.py         # silkscreen every connector pin's function
python3 tools/drc_exclusions.py     # gate: is any DRC violation NOT accepted?
```

**`drc_exclusions.py` is the gate to run before a fab upload.** It matches every
DRC violation against an explicit table of accepted ones, each with a written
reason, and exits nonzero on anything unrecognised. It cannot bless a new
violation — that is the point. Seven known-good warnings are worse than none,
because the eighth arrives looking exactly like the noise.

> **KiCad's project save can silently drop design data.** Saving after the DRC
> exclusions were made removed two netclass patterns — `HighCurrent →
> /power/DC_IN` and `Power → +5V_RAW`, the exact gaps fixed earlier in this
> project — and emptied `track_widths`. `check_board.py` check 9 caught it;
> nothing in KiCad's own DRC would have. **Run `check_board.py` after any KiCad
> session that saves the project**, not just after tool runs.

**Excluding is done in KiCad, not by the tool.** Right-click a violation in the
DRC panel → **Exclude this violation**, save, then run the tool: it attaches the
documented reason to what KiCad wrote and prunes entries that no longer match a
violation. It never invents a key.

That division exists because the other way was tried and half-failed. KiCad
stores `["<type>|<x_nm>|<y_nm>|<uuid_a>|<uuid_b>", "<comment>"]`, and a version
of this tool synthesised the key from the DRC report. **Three of seven took.**
Type and uuids were right every time; the *coordinate* was not — it is the
footprint anchor for C4/C6/L1, but for A1/A2 it is neither the anchor nor the
bounding-box centre (both carry an identical x of 118.6825 mm matching no
obvious feature), and for `silk_overlap` it is neither item's reported
position. Not reconstructible, so not synthesised. Matching uses
(type, uuid_a, uuid_b), which is stable; the coordinate is carried verbatim.

**Lock anything you place or adjust by hand — copper and silkscreen both.** `cycle.py` strips everything unlocked and
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