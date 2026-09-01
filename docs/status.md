# Status

Where the board is, and what happens next. Read this first.

## ▶ RESUME HERE — 2026-09-01

**The board is routed, filled, silkscreened and fab-ready.** The 2026-08-21
strip-and-re-place is complete: re-placed into the upper board, re-routed,
ground stitched, silkscreen cleared, and `fab_package.py` reports **ready**.

**State now**, every figure re-derived from the board rather than carried
forward:

| | |
| --- | --- |
| schematic parity | **0** |
| unconnected | **0** |
| `check_board.py` | **12/12** |
| DRC, plain | **2** — `lib_footprint_mismatch` on A1 and A2 only, see below |
| tracks / vias / zones | **957** (4186 mm) / **167** / 10, all filled |
| tracks under the 0.20 mm rule | **0** |
| ground | F.Cu 26 islands, main 5003.5 mm²; B.Cu a single 11448.3 mm² plane |
| floating ground copper | **0** — every island carries a via or a through-hole GND pad |
| footprints | **135** |
| DNP | **0**, and check 12 fails if any reappears |

**The two remaining DRC lines are A1 and A2, and they are metadata.** Verified
2026-08-22 by diffing all 20 pads of each against
`caryatid.pretty/DaisySeed_Socket_A_1x20.kicad_mod`: **none differ**. What
differs is what KiCad adds when a footprint is placed — `path`, `sheetfile`,
`sheetname`, two extra property fields and their hide flags — none of it copper,
and none of it removable without breaking the schematic link.
`drc_exclusions.py` accepts them with reasons and reports **0 new, 5 accepted**.
They still appear in plain DRC because the project file carries only three
exclusion keys; adding the other two is a one-time right-click → *Exclude this
violation* in pcbnew's DRC panel. The tool will not synthesise those keys — it
tried once and got the coordinate wrong for exactly these two.

**R45 was a third such line and was FIXED rather than excluded**, 2026-08-22.
Its pads were stored at 270° against a footprint at 90° — 180° relative, where
`Resistor_SMD` has 0° — and it was the only one of 64 0603 resistors on the
board like that. The half turn was harmless, since a 0.800 × 0.950 mm rectangle
is unchanged by it and both pad centres are identical before and after, which is
precisely why excusing it was wrong: a lone outlier that costs nothing to
normalise should be normalised. It picked up the flip when `3fe330e` rotated it
beside J9/J10.

### Ordered, and the boards are here

**Ordered 2026-08-23. The boards arrived 2026-09-01**, with the battery holders
and the jumpers. caryatid is no longer a design, it is five physical boards.
Order detail, cost reconciliation and the ENIG decision are in
[`jlc-order-2026-08-23`](../discovery/findings/jlc-order-2026-08-23.yaml).

*This section read "What is left before ordering: 1. exclude A1 and A2 in DRC,
2. Order" from 2026-08-22 until 2026-09-01, nine days after the order was
placed. It was stale in the one file that is meant to be read first when
picking this project up cold. The A1/A2 DRC exclusion was never done and is now
moot for this batch: they are metadata, not copper, and the boards are made.*

**BT1 fits.** The 65-68 mm vs 69.48 mm conflict that hung over the battery
since 2026-08-23 is closed: the holders are in hand and the cell seats. MPD's
stated range is conservative rather than dimensional, as the STEP analysis
predicted. See
[`bt1-cell-fit`](../discovery/findings/bt1-cell-fit.yaml), and seat all five
pairs before assembly rather than trusting the one that was tried.

### What is left now

1. **Screws for the battery holders**, the only part still unsourced. M3, and
   the length wants the holder measured rather than guessed. See `bt1-cell-fit`.
2. **Bring up a board.** Nothing in this repo has been powered.

Nothing else is outstanding on the design. The boost hot loop, R45's placement and the necked
tracks were all checked on 2026-08-22 and none needed work — see below.

## The board *was* routed, at `snapshot/routed-2026-08-21`

Kept here because it is worth knowing the electrical result was reachable on
this outline. At that tag every check was at zero:

| | |
| --- | --- |
| real unconnected connections | **0** |
| zone-to-zone unconnected | **0** |
| shorts, clearance, hole clearance | **0** |
| tracks under the 0.20 mm rule | **0** |
| floating ground copper | **0** |
| `tools/check_board.py` | **pass** |

150 × 90 mm, two layers, 135 footprints, all on the front. Ground pour both
sides, power nets around U1 and U2 poured from hand-drawn outlines rather than
routed — see [ADR 0008](decisions/0008-board-outline-and-layer-count.md).

**None of that copper is on the board now.** The outline, the layer count, the
pour strategy and the footprint set carry forward. The route does not.

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

   **Seven connector references moved** to make room: J6, J7, J8, J9, J10, J19
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

5. **Manufacturing readiness** — **was ready; reopened by ADR 0010.**

   > **Everything in this section describes the board as of `ad6a54d`**, before
   > the right-channel jumpers. It is kept rather than deleted because the
   > *gates* are unchanged and the cost work still stands — only the counts move.
   > Re-derive them by re-running the tools after the PCB is updated from the
   > schematic; do not hand-edit the numbers.

   `python3 tools/fab_package.py --apply` writes `local/fab/` and exits nonzero
   while anything is missing. It exited zero at `ad6a54d`.

   | gate | |
   | --- | --- |
   | DRC, plain | **2** — `lib_footprint_mismatch` A1/A2, metadata only |
   | DRC + `--schematic-parity` | **0 parity**, **0 unconnected** |
   | `check_board.py` | **12/12** over 135 footprints |
   | `drc_exclusions.py` | **0 new**, 5 accepted with reasons |
   | `verify_parts.py` | **0 of 43 flagged** against JLC's live data, 2 pre-order |
   | LCSC coverage | **127 of 127** placed (BT1 self-fit, see below) |

   **Package** — `local/fab/caryatid-fab.zip`, 14 files, 373 kB: 9 Gerber
   layers, drill, drill map, job file, `cpl.csv`. `bom.csv` sits beside it.
   Deliberately *not* courtyard, fab, adhesive or Eco layers, which an
   unrestricted export emits — and *not* `self-fit.csv`, which is the owner's
   shopping list and would only confuse the assembler.

   **Always run DRC with `--schematic-parity`.** Plain `kicad-cli pcb drc` does
   not check it and once hid 7 issues.

   **Board** 150 × 90 mm, 2 layers, 135 footprints, 957 tracks (4186 mm),
   167 vias. **BOM** 42 lines, **127 placed by JLC**, plus BT1 self-fit.

   **NOTHING IS DNP.** An earlier revision of this section read "47 lines, 91
   placed, 32 DNP excluded by design". [ADR 0010](decisions/0010-nothing-is-dnp.md)
   overturned that: DNP was an instruction to a person, and JLC fits the
   through-hole parts too. `--exclude-dnp` stays on both exports as a guard
   rather than a filter.

   **BT1 is `self_fit`, which is not DNP.** A DNP part is one the board is
   complete without; a self-fit part is one it is **not** complete without.
   BT1 goes to `self-fit.csv` because Digi-Key beat JLC's pre-order on both
   price and lead time, not because it is optional.

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

   **Superseded 2026-08-23 by three real orders.** Every estimate in this
   section is history; these are actuals:

   | | five boards | per board |
   | --- | --- | --- |
   | JLC, delivered | **$306.95** | $61.39 |
   | Orbtronic cells | $67.45 | $13.49 |
   | Digi-Key, delivered | $49.56 | $9.91 |
   | **total** | **$423.96** | **$84.79** |

   **The estimate was fine and the budget was not.** `cost_estimate.py`
   predicted $161.68 of merchandise against $176.24, out by 9%. It models
   merchandise only: shipping, customs duties, payment fee and sales tax added
   $130.71 to the JLC order, a 74% uplift, and both imports carried a tariff.
   See [`JLC-order-2026-08-23`](../discovery/findings/jlc-order-2026-08-23.yaml)
   and `~/.claude/contexts/ideocentric/_org.md`.

   > **A superseded figure lived here: "$5.24/board in components."** Do not
   > reinstate it. Beware `leastNumberPrice` in the JLC API — it reads $0.101 for
   > the Seed socket and $0.7533 for BT1, against real ladder prices of $0.338
   > and $4.86. It is not the price you pay.

   The fee is per unique part, **not per BOM line**. The **22** that stay
   Extended cannot move without a real compromise: connectors are absent from
   the Basic library, R3/R4/R7/R8 are E96 values that set charge current and
   boost output voltage, and C1 is 25 V X7R, which is a demanding part in 0805.
   (22 Extended / 20 Basic as of 2026-08-23; it read 20 before ADR 0010 fitted
   the right channel.)

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

**Unblocked 2026-08-20 by dropping BT1 from the assembly.** JLC quoted a
**21-day** turnaround on the BT1 pre-order. Rather than wait, it is now
**self-fit**: bought from Digi-Key and hand-soldered.

| | code | qty for 5 | unit | |
| --- | --- | --- | --- | --- |
| A1, A2 sockets | `C2897383` | 10 | $0.338 | pre-order, 1353 in stock |
| BT1 holder | Digi-Key 3029216 | 5 | **$3.47** | **not via JLC** |

**Nothing is lost off the SMT line.** BT1 is `manualWeld` — the assembler would
have hand-soldered it anyway. It is two through-hole joints (`VBAT`, `GND`,
72.9 mm apart) plus two M3 bolt holes at 55.61 mm, which the footprint already
carries. Digi-Key is *cheaper* than the pre-order as well as immediate: $3.47
against $4.8616.

**Substituting a different holder was considered and rejected.** BT1's footprint
is dimensionally specific, so swapping the part is a board change — self-fitting
the known-good part is strictly safer than fitting an available unknown.

> **BT1 is NOT DNP.** It is populated on every board; it is simply bought and
> soldered by the owner. `self_fit` in `lcsc.yaml` records this and
> `fab_package.py` strips it from `bom.csv` and `cpl.csv`, writing
> `self-fit.csv` as the shopping list. Marking it DNP instead would tell the
> assembler no part is fitted, which is false and would propagate.

Stock for the other 34 JLC codes was checked at qty 5 and clears.

**When the quote lands, reconcile rather than eyeball it:**

```sh
.venv/bin/python tools/cost_estimate.py 5 --quote <total>
```

It prints what the real number implies for each line it had to guess, since
parts is the one line that cannot be the source of the error. Correct `RATES`
and `PCB_FAB` in the tool from the answer and every future quantity improves.

**Two lines are worth checking specifically**, because they are where the
estimate is most likely wrong:

1. ~~**PCB fab.**~~ **Measured 2026-08-23.** `PCB_FAB[5]` is $42.56 with ENIG,
   derived by reconciling the tool against a real $176.24 merchandise total.
   Every other quantity in that table is still a placeholder.
2. ~~**Whether the Extended fee is per unique part or per BOM line.**~~
   **It was never open.** Per unique part, stated in
   `~/.claude/contexts/ideocentric/_org.md` and implemented in
   `cost_estimate.py` all along, while this list and the worklog carried it as
   unresolved. Closed 2026-08-23.
3. **What a landed cost actually is.** The tool models merchandise. Shipping,
   duties, fees and tax were 74% on top at JLC and 19% at Digi-Key, and nothing
   models them. This is the live one.

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

> ### Opening this board in KiCad damages `caryatid.kicad_pro`
>
> **It has happened twice.** Saving from the GUI silently:
>
> - **deletes netclass patterns** — `/power/DC_IN` (HighCurrent) and `+5V_RAW`
>   (Power) both went. That is how a rail ends up on a 0.25 mm track.
> - **empties `track_widths`** to `[]`
> - **wipes every DRC exclusion comment** to `""`, losing the recorded reason
> - **re-adds stale exclusions** — two `silk_overlap` entries came back
>   referencing violations that were *fixed* in `fd90beb`, not accepted
>
> **After any KiCad session, before committing:**
>
> ```sh
> git diff hardware/pcb/caryatid.kicad_pro     # expect NOTHING unless you changed a setting
> python3 tools/check_board.py                 # check 9 catches the netclass loss
> python3 tools/drc_exclusions.py              # catches stale or uncommented exclusions
> ```
>
> If the diff shows only the damage above, `git checkout hardware/pcb/caryatid.kicad_pro`.
> Nothing is lost — the project file holds settings, not design data.

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
- **`snapshot/routed-2026-08-21`** — the last board with copper on it: 949
  tracks, 203 vias, 10 filled zones, parity 0. Stripped by `907fa83` so the
  route could be redone from a rebalanced placement. Its tag message carries
  the restore command.

Plus timestamped copies in `local/backups/`, which is gitignored.