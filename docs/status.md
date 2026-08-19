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
2. ~~**Component silkscreen.**~~ **Done** — D1's reference moved from below the
   body to above it, `-2.5` to `+2.5`, the exact mirror; U1's went `0` to
   `0.2875` on X. Both clear the 0.25 mm rule outright.

   The other 106 hidden references were residue of "hide the back references",
   from when every SMD part was on the back face — a rule that no longer
   describes the board. `tools/ref_silk.py` swept them: **71 are now shown**
   (65 at 1.0 mm, 2 at 0.9, 4 at 0.8), taking the board from 25 visible
   designators to 96.

   **25 stay hidden because nothing fits** — C11–C14, C16, C17 and eighteen
   resistors in the audio network, where 0603 parts sit on a 1.5 mm pitch and a
   two-character label is wider than the gap. They are left hidden rather than
   forced: a designator overlapping a pad prints ink on a solderable surface,
   which is worse than no designator. Identify those parts from `cpl.csv` in
   the fab package, or from the F.Fab layer in KiCad — every reference is still
   on F.Fab whether or not it prints.

   H1–H4 and FID1–3 are skipped by design — mounting holes identify no part,
   and fiducials are machine-read. U2, L1 and FB1 stay hidden deliberately,
   because their labels collide with their own outlines and get clipped by
   solder mask.
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
4. ~~**Logo and font from absonus**~~ **Done, including the mark.** The ensō is
   on F.SilkS at **18 mm, centred (174, 55.5)**, converted from
   `local/enso-oro.svg` by `tools/svg_to_silk.py` — 153 filled polygons,
   12 255 points. The wordmark `caryatid` + `v0.1` is separately at the bottom
   right by `tools/branding.py`.

   **The artwork was never in the v0.1 archive.** absonus v0.1 has zero images,
   zero silk polygons and no logo footprint across all three of its boards —
   which is why the earlier answer was "there is nothing to import". The mark
   arrived in **v0.3**, and the source is the SVG.

   **Size is measured, not chosen**: 18.50 × 18.71 mm on the fabricated
   absonus v0.3, read off `local/absonus-v0.3-pcb.pdf` at 600 dpi against its
   stated 3.6000 in width. caryatid's largest clear front-side square is 18 mm
   — within 3%.

   That measurement overturned an analysis of mine. Opening the artwork at
   JLC's 0.15 mm silk floor removes 27% of the ink at 18 mm and fragments the
   rings, which said **unusable**. A board fabricated at 18.5 mm says
   otherwise. The model was worst case; the board is evidence.

   `.venv` is required for this tool (`svgelements`), and is gitignored.

5. **Manufacturing readiness** — **ready.**

   `python3 tools/fab_package.py --apply` writes `local/fab/` and exits nonzero
   while anything is missing. It exits zero.

   | gate | |
   | --- | --- |
   | ERC | **0** |
   | DRC, plain | **0** violations, 0 unconnected, 0 footprint errors |
   | DRC, all severities + `--schematic-parity` | **0 parity**, 5 excluded |
   | `check_board.py` | **10/10** over 131 footprints |
   | `drc_exclusions.py` | **0 new**, 5 accepted with reasons |
   | `verify_parts.py` | **0 of 37 flagged** against JLC's live data |
   | LCSC coverage | **92 of 92** |

   **Package** — `local/fab/caryatid-fab.zip`, 14 files, 279 kB: 9 Gerber
   layers, drill, drill map, job file, `bom.csv`, `cpl.csv`. Deliberately *not*
   courtyard, fab, adhesive or Eco layers, which an unrestricted export emits.

   **Always run DRC with `--schematic-parity`.** Plain `kicad-cli pcb drc` does
   not check it and once hid 7 issues.

   **Board** 150 × 90 mm, 2 layers, 131 footprints, 926 tracks, 192 vias.
   **BOM** 48 lines, 92 placed — 32 DNP excluded by design, the audio network
   being fitted per instrument.

   **Cost** — re-derived 2026-08-18 from live price ladders by
   `tools/cost_estimate.py`, which selects the correct price band for the actual
   order quantity and respects MOQ:

   | | 5 boards | 10 boards |
   | --- | --- | --- |
   | parts (exact) | **$62.42** | **$119.90** |
   | per board | $12.48 | $11.99 |
   | estimated total | **~$169** | **~$249** |
   | per board | **$33.77** | **$24.88** |

   **$68 is fixed regardless of quantity** — an $8 setup fee plus 20 Extended
   parts at ~$3 each. That is 40% of a 5-board order, which is why the second
   five cost $15.99/board against $33.77 for the first five.

   > **A superseded figure lived here: "$5.24/board in components."** Do not
   > reinstate it. Beware `leastNumberPrice` in the JLC API — it reads $0.101 for
   > the Seed socket and $0.7533 for BT1, against real ladder prices of $0.338
   > and $4.86. It is not the price you pay.

   The fee is per unique part, **not per BOM line**. The 20 that stay Extended
   cannot move without a real compromise: connectors are absent from the Basic
   library, R3/R4/R7/R8 are E96 values that set charge current and boost output
   voltage, and C1 is 25 V X7R, which is a demanding part in 0805.

   **Assembly splits in two.** `assemblyModeBatch` separates the SMT line from
   hand soldering: **100 SMT joints and 111 through-hole joints per board**, the
   through-hole being both Seed sockets, BT1 and all 17 JST/IDC connectors —
   8 codes, 19 parts. Full turnkey is the chosen route, so JLC solders both.

   **Two parts are pre-order**, both confirmed acceptable:

   | | | |
   | --- | --- | --- |
   | BT1 | `C5339083` | stock **0** |
   | A1, A2 | `C2897383` | stock 1403 — **pre-order regardless of stock** |

   > **Pre-order status is a recorded fact, not a derived one.** The JLC API
   > cannot tell you: `componentSource`, `warehouseCode` and
   > `assemblyComponentFlag` are uniform across all 36 parts here, and
   > `canPresaleNumber` does not separate them either. A stock-0 test catches
   > BT1 and misses the sockets entirely. `verify_parts.py` therefore reads the
   > flag back out of `lcsc.yaml`, where it is written down from JLC's own parts
   > library.
   >
   > **Confirmed again 2026-08-18, the hard way.** BT1 reports stock 0 *and*
   > `canPresaleNumber` 0 on the public endpoint, and is nonetheless orderable
   > through the logged-in parts library at **$4.8616** — below the $5.0468 the
   > public ladder quotes. The public API cannot see the pre-order route at all.
   > That is twice an automated test has overruled the human record and lost.

## Waiting on: the quote

**Decided — 5 boards, full turnkey.** 10 was costed and rejected for now: it
would mean changing the battery-holder pre-order quantity, and the holder is the
only long-lead item. Everything else can be re-quoted at any quantity right up
to order time, so nothing else has to be decided early.

**Blocked on** the pre-ordered holders appearing in the JLC parts library. The
quote cannot be raised until they do.

| pre-order | code | qty for 5 | unit |
| --- | --- | --- | --- |
| BT1 holder | `C5339083` | 5 | $4.8616 |
| A1, A2 sockets | `C2897383` | 10 | $0.338 |

Stock for the other 35 codes was checked at qty 5 and clears; BT1 was the only
short line, which is what the pre-order resolves.

**When the quote lands, reconcile rather than eyeball it:**

```sh
.venv/bin/python tools/cost_estimate.py 5 --quote <total>
```

It prints what the real number implies for each line it had to guess, since
parts is the one line that cannot be the source of the error. Correct `RATES`
and `PCB_FAB` in the tool from the answer and every future quantity improves.

**Two lines are worth checking specifically**, because they are where the
estimate is most likely wrong:

1. **PCB fab.** 150 × 90 mm is past JLC's 100 × 100 cheap tier, so it is
   area-priced and the tool does not model their area formula. `PCB_FAB` is a
   flat placeholder.
2. **Whether the Extended fee is per unique part or per BOM line.** 20 unique
   Extended parts at $3 is $60; counted per line it looks like about half that.
   Getting this backwards understated a figure once already here.

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
python3 tools/fab_package.py        # gerbers, drill, BOM, CPL; refuses if unsourced
.venv/bin/python tools/search_list.py --apply   # JLC worklist for what is left
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