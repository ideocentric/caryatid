# Worklog

Newest last. Session state lives here and in the ledger, not in conversation.

## 2026-08-19 09:45 — Silkscreen references, enclosure measured, sourcing recorded, licensing settled across both repos

**Completed:**
- **Component references shown.** 71 of 96 hidden designators placed by
  `tools/ref_silk.py` (65 at 1.0 mm, 2 at 0.9, 4 at 0.8), taking the board from
  25 visible to 96. 25 left hidden deliberately — 0603 parts on 1.5 mm pitch in
  the audio network, where forcing a label prints ink on a solderable surface.
  All still carry `${REFERENCE}` on F.Fab. DRC unchanged: 5 excluded
  `lib_footprint_mismatch`, 0 silk_overlap. `check_board.py` 10/10.
- **`BUD-CU-477-interior` opened and confirmed.** Enclosure measured in hand,
  superseding two derived figures. Floor 178 × 110, height 34.0, plate 2.16
  ±0.1, perimeter lip 6.0/4.0. Board mounts 5 mm from the left wall — not
  centred — for power-button clearance *and* left-hand balance. The 12 mm
  latching switch descends 23 mm and sits in the reserved 28 mm strip
  (confirmed, was inference). Corrected the drill instruction, which said
  "±40/±70 from the floor centre" and would have put the board 9 mm into the
  button's space.
- **`JLC-BOM-sourcing` opened.** 36 codes, 16 Basic / 20 Extended, 100 SMT and
  111 through-hole joints per board. Parts $62.42 at qty 5 / $119.90 at qty 10,
  exact from live ladders. Retired the unsourced "$5.24/board" figure, which is
  roughly what the API's misleading `leastNumberPrice` field yields.
- **`tools/cost_estimate.py`** added — live ladders, measured joint counts,
  guesses isolated in one block, `--quote` reconciles against a real number.
- **Licensing made machine-readable.** caryatid read as `NOASSERTION` while
  public because `LICENSE.md` wrapped the licence text in a table. Root
  `LICENSE` is now the verbatim CERN-OHL-S v2; the explainer moved to
  `LICENSING.md`. GitHub now reports `CERN-OHL-S-2.0`.
- **Four stale caryatid docs** and **three stale loa docs** corrected — all
  still said the licence was unsettled or the repo private.
- **loa ADR 0007 written and accepted**: loa's `hardware/` returns to
  CERN-OHL-S-2.0, matching caryatid. Five `.scad` SPDX headers, licence text
  reinstated, READMEs restated. Also corrected two statements that had become
  hazardous — `hardware/README.md` claimed the power supply derives from
  Adafruit's PowerBoost (it does not, since caryatid), and
  `03-hardware-design.md` said deriving from their schematic "is fine", which
  under CERN-OHL-S is false.

**In flight:** nothing. Both working trees clean, both pushed.

**Open questions:**
- Whether the Extended loading fee is charged per unique part ($60) or per BOM
  line (~half that). Got backwards here once already; moves the total ~$30.
- The PCB fab estimate. 150 × 90 mm is area-priced past JLC's 100 × 100 tier and
  `cost_estimate.py` does not model the formula — `PCB_FAB` is a placeholder.
- Bench measurements still open, and deliberately not blocking: handset capsule
  DC resistance, J4 green die at 3.0 V, switch lamp current. `docs/audio.md`
  defers the capsule question past fabrication by design (U4 is DNP with a
  bypass), so these change resistor values, not the board.

**Next step:** when the pre-ordered battery holders appear in the JLC parts
library, raise the quote for **5 boards, full turnkey**, then run
`.venv/bin/python tools/cost_estimate.py 5 --quote <total>` in the caryatid repo
and correct `RATES` / `PCB_FAB` from what it reports. Pre-orders are
`C5339083` ×5 @ $4.8616 and `C2897383` ×10 @ $0.338.

## 2026-08-20/21 — ADR 0009, the left mic channel behind jumpers

**Not logged at the time.** Twenty-three commits, `5bc99d2..ad6a54d`, spanning
the JLC BOM/CPL format work, BT1's move to self-fit, and all of ADR 0009. The
commit messages carry the detail; this entry exists so the gap in the worklog is
visible rather than silent. The durable outcomes are in
[ADR 0009](../docs/decisions/0009-mic-input-is-jumper-selected.md),
[audio.md](../docs/audio.md) and
[mic-configurations.md](../docs/mic-configurations.md).

## 2026-08-21 — ADR 0010: the right mic channel is jumpered, and nothing is DNP

**Completed:**

- **[ADR 0010](../docs/decisions/0010-nothing-is-dnp.md) written and accepted.**
  Zero `dnp` on any sheet. BT1 is not an exception — it is `self_fit`, which is
  an assembly routing decision, not a population one.
- **The right mic channel is a full mirror of the left.** JP4 bias / JP5 path /
  JP6 gain, plus **R68 392R**, the one part that is not a translation: the left
  has two gain legs (R58 1k, R67 392R) and the right had only R62, so without
  R68 there was nothing for JP6 to select.

  **This was not simply "clear the DNP".** The right channel is laid out as an
  exact mirror of the *pre-jumper* left, +149.86 mm in Y, so it inherited both
  mutually exclusive pairs — 2k2-to-3V3A against 220R-to-5V on `MIC_R`, op-amp
  output against raw bypass on `AUDIO_IN_R`. Populating it without jumpers would
  have shipped the exact defect ADR 0009 exists to prevent.
- **R48, R50, R64, R66 deleted.** Their value is `open`; no supplier ships one,
  so they could not be populated to satisfy the rule. What they provided is
  covered: R47/R49 1k *is* the earpiece attenuator, and the WM8731 line PGA
  reaches −34.5 dB, which is more pad than a resistor was going to give and is
  adjustable at run time. **R66 was on the wrong node** — it tapped `AUDIO_IN_R`,
  downstream of where JP5 lands, so it would have padded the op-amp output too.
  A latent defect removed alongside a DNP.
- **R43–R46 assembled.** Both exclusions failed on the numbers: a UART line
  idles high so a 4k7 pull-up holds it where it belongs, and A4/A5 reach only
  J9/J10 (J5 carries A0–A3, A6–A9), checked against the netlist.
- **`check_board.py` check 12** — no `dnp` on any sheet. The one schematic check
  in that tool, because nothing else has an opinion: ERC ignores `dnp`, DRC
  never sees it, and the only symptom of one reappearing is a BOM line that
  quietly stops being fitted. Verified by injecting one.
- **`tools/stale_tracks.py`** — finds tracks left sitting on a pad whose net
  moved. **Calibrated against the known-answer case**, the board immediately
  before `0491e70` where DRC found exactly four: 0.001 mm margin finds 2,
  0.10–0.15 finds 4, 0.20 finds 6 including legitimate routing. 0.15 is
  `min_clearance` from the project file, not a tuned number.
- **Thirteen documents corrected**, including two statements that had gone
  false: `audio.md`'s "the right stays DNP", and `sourcing.md`'s R52/R54
  dissipation note, which said "they are not populated now" when both now are.

**Verified:** ERC 0 violations at `--severity-all` after each of the three
schematic edits; netlist diff shows 99 of 107 nets byte-identical with 6 new and
8 changed, all intended (`discovery/evidence/2026-08-21-audio-netlist-diff.txt`);
0 `dnp` across all five sheets; `check_board.py` 12/12.

**In flight:** **the schematic is ahead of the board, deliberately.** DRC reports
**28 schematic parity issues** and that is exactly this. `kicad-cli` has no
update-from-schematic, so the next steps need the GUI and are listed in the
RESUME HERE block at the top of [status.md](../docs/status.md).

**Open questions:**

- **R52/R54 dissipation, now live rather than hypothetical.** 92 mW on a 100 mW
  0603 if a carbon capsule sits at 0.5 V, and both are populated. The carbon
  jumper position and the `MIC_RTN` hook-switch gate keep it from being urgent.
  Measure a capsule, then decide whether those two want an 0805.
- **`MIC_RTN` is shared by both channels** — one gated return, two capsules. A
  stereo carbon pair puts both bias currents through one switch contact. Correct
  arrangement (the gate belongs to the handset), worth knowing before sizing it.
- The manufacturing counts in `status.md` are stale by design until the board is
  updated. Re-run `fab_package.py`; do not hand-edit them.
- Everything still open from 2026-08-19: the Extended fee basis, the PCB fab
  area price, and the three bench measurements.

**Next step:** open KiCad, **Update PCB from Schematic**, place JP4–JP6 and R68,
delete the four removed footprints, then **run `tools/stale_tracks.py` before
routing anything** — five pads change net and KiCad leaves the old tracks
behind. Re-route, refill, DRC with `--schematic-parity`, `check_board.py`,
`jumper_legend.py --apply`, `fab_package.py`.

## 2026-08-22 18:30 — Silkscreen finished, necks widened, last 3 parts sourced; fab package READY

**Completed:**

- **Silkscreen closed out.** J12 pin labels shortened to R/G/B on their pads;
  J13 vertical at 1.3 mm pitch (the 3-row stagger ran off the board); reference
  left / role right on one bottom row for J6-J10, J12, J15, J19; J14/J17/J18 on
  a vertical J19-style baseline at x 197.8 with their pin labels right-justified
  per jack; role labels centred on the BODY outline, not a bounding box that
  swallowed the pin-1 marker. `15915bf`, `28c54f1`.
- **All 5 necked tracks widened to 0.20 mm** — they were never load-bearing.
  `widen_necks.py` was verifying against a pour it had not recomputed, so one
  false positive reverted four sound repairs. It now runs ZONE_FILLER between
  the widen and the check. `221b236`.
- **One GND via at (67.52, 55.8)** stitching the 5.56 mm2 F.Cu pocket at U1's
  south-west corner to the plane, placed clear of the EP. `6efdcfb`.
- **JLC-BOM-sourcing: 127 of 127 parts covered.** R45 -> C4211 (already stated
  in sourcing.md), R43/R44 -> C23162 (a NEW selection, mine, catalogue-verified).
  `fab_package.py` reports **ready**; `local/fab/caryatid-fab.zip` written,
  373 kB, 14 files. Evidence: `2026-08-22-lcsc-r43-r44-r45.json`,
  `2026-08-22-fab-readiness.txt`.
- **R45's pad angle normalised** 270 -> 90 (180 relative -> 0). It was the only
  one of 64 0603 resistors like that. I put it in drc_exclusions' allow-list
  first; that was wrong and Matt's question caught it. Plain DRC 3 -> 2.
- **BUD-CU-477-interior:** the "R45 sits 1.22 mm from the board edge" concern is
  RETIRED as never-true. Measured 5.500 mm, with J15 and J9 both reaching
  further toward that edge. It was never in any record, which is why it survived
  four sessions.
- **Checked, no work needed:** boost hot loop against SLVSF14B Fig 10-1 —
  U2.6->C6.1 1.785 mm, C6.2->U2.4 1.834 mm, perimeter 6.519 mm, returning
  through a shared 23.1 mm2 F.Cu island rather than a track; SW node 3.717 mm
  and 0.612 mm2 of copper; C5 2.465 mm off the VOUT input pin.
- **status.md and sourcing.md re-derived from the board.** status.md still said
  "the board is unrouted, on purpose" and reported 0 tracks.

**Verified:** DRC 0 unconnected, 0 parity, 0 clearance, 0 track_width, 0 silk;
2 lib_footprint_mismatch (A1/A2 only). `check_board.py` 12/12 over 135
footprints. `drc_exclusions.py` 0 new, 5 accepted. `verify_parts.py` 0 of 43
flagged, 2 pre-order. 957 tracks (4186 mm), 167 vias, 10 zones filled; F.Cu 26
islands main 5003.5 mm2, B.Cu one 11448.3 mm2 plane; 0 DNP.

**In flight:** nothing. Working tree clean, both repos pushed.

**Open questions:**

- **A1/A2 need a one-time right-click exclude in pcbnew's DRC panel.** Their
  mismatch is metadata only — all 20 pads of each were diffed against
  `caryatid.pretty/DaisySeed_Socket_A_1x20.kicad_mod` and NONE differ; what
  differs is `path`, `sheetfile`, `sheetname` and two property fields KiCad adds
  on placement. `drc_exclusions.py` will not synthesise the keys: it tried once
  and got the coordinate wrong for exactly these two.
- **C23162 (4k7, R43/R44) is a tooling choice, not Matt's.** Commodity 0603 1%
  Basic, same Uniroyal series as C4211, catalogue-verified — but it is the one
  code in the BOM nobody stated. Worth a glance before ordering.
- **R52/R54 dissipation** — 92 mW on a 100 mW 0603 if a carbon capsule sits at
  0.5 V, both populated. Measure a capsule, then decide on 0805. (Carried.)
- **`MIC_RTN` is shared by both channels** — one gated return, two capsules.
  (Carried.)
- Everything still open from 2026-08-19: the Extended fee basis, the PCB fab
  area price, and the three bench measurements.

**Next step:** open `hardware/pcb/caryatid.kicad_pcb` in pcbnew, run DRC from
the panel, right-click each of the two `lib_footprint_mismatch` violations on A1
and A2 and choose **Exclude this violation**, save, then run
`python3 tools/drc_exclusions.py --apply` to attach the documented reasons.
Plain DRC then reads zero and `local/fab/caryatid-fab.zip` is orderable as it
stands.

## 2026-08-23 — A1/A2 excluded; plain DRC reads zero; tool conventions written down

**Completed:**

- **Matt excluded the A1 and A2 `lib_footprint_mismatch` violations** in
  pcbnew's DRC panel. The keys landed at x 115.853, y 66.248 and 76.265 — the
  coordinates `drc_exclusions.py` could not reconstruct and rightly refused to
  synthesise. `drc_exclusions.py --apply` attached their documented reasons:
  5 exclusions kept, 2 given a reason, **plain DRC now reports 0 violations**.
- **`docs/conventions.md` written.** Eight rules that apply across tools, each
  with the failure that produced it and the measurement that proves it. They
  had been buried in individual docstrings where the next tool to repeat the
  mistake could not see them. Linked from the README's "Start here" table.
  Rule 1 is the one that prompted this: **recompute the zone fill before
  verifying a copper change**, which cost four sound repairs when
  `widen_necks.py` judged widened tracks against a pour that had not moved.

**Verified:** plain DRC **0 violations**, 0 unconnected, 0 parity;
`drc_exclusions.py` 0 new, 5 accepted; `check_board.py` 12/12;
`fab_package.py` **ready**, 127 of 127.

**In flight:** nothing.

**Open questions:** unchanged — C23162 (4k7, R43/R44) is a tooling choice rather
than Matt's and is worth a glance before ordering; R52/R54 dissipation; shared
`MIC_RTN`; and the three items carried from 2026-08-19.

**Next step:** order. `local/fab/caryatid-fab.zip` (373 kB, 14 files) plus
`bom.csv` and `cpl.csv` beside it are current and every gate is green. BT1 is
bought separately — `self-fit.csv`, Digi-Key 3029216.

## 2026-08-23 — /bootstrap Phases 1–2; the Extended fee was never still open

**Completed:**

- **`/bootstrap` Phase 1 (inventory) and Phase 2 (scaffold).** `engagement.yaml`
  written here and in loa, both git-excluded via `.git/info/exclude` per the
  rekor and gcc precedents — this repo is published, so working configuration
  stays out of it. `CLAUDE.local.md` created here for the first time: caryatid
  is the canonical clone where all work happens and it had no local context at
  all, only loa's.
- **Voice recorded.** caryatid is `voice: professional`; loa, absonus and
  baby-borg are `creative`, carrying the Nervous Gender Reloaded personality.
  Confirmed by Matt 2026-08-23. `ideocentric/_org.md` currently lists all four
  together under one "Hardware projects" heading without distinguishing them —
  a refinement is proposed there but NOT yet applied.
- **Phase 3 deliberately narrowed, and the narrowing is not new.** A mass
  salvage of ~700 numeric claims across 15 documents into `unverified` records
  was refused. `discovery/README.md` already scopes this ledger to facts the
  repo cannot check for itself, and `ideocentric/_org.md` carries the same
  exception for hardware projects. DRC, `check_board.py`, `verify_parts.py` and
  `fab_package.py` verify the board's numbers continuously; records would be a
  staler second copy.

**Corrected:**

- **The Extended loading fee has NOT been an open question since before this
  worklog said it was.** Carried here as unresolved three times — "whether the
  fee is charged per unique part ($60) or per BOM line" — while
  `~/.claude/contexts/ideocentric/_org.md` states it is **per unique part, not
  per BOM line**, and `tools/cost_estimate.py` has implemented exactly that
  (`"extended_fee": 3.00, # per UNIQUE Extended part`). Settled in two places,
  carried as open in a third. **It is closed.**
- `discovery/README.md` said the sourcing record covers "The 36 LCSC codes". It
  is 43. Now dated rather than restated.

**In flight:** Phase 2 is otherwise done. Two `~/.claude` edits are PROPOSED and
not applied — refining `ideocentric/_org.md`'s voice section to distinguish
caryatid from the instruments, and filling the 8-line `ngr/_org.md` stub, which
needs NGR's actual tone and vocabulary from Matt rather than my invention.

**Open questions** — five, down from the six carried yesterday:

- PCB fab area price: 150 × 90 mm is past JLC's 100 × 100 tier and
  `cost_estimate.py`'s `PCB_FAB` is a placeholder. Needs a quote.
- Handset capsule DC resistance (bench).
- J4 green die at 3.0 V (bench).
- Switch lamp current (bench).
- Part behaviour no catalogue field states, per `verify_parts.py`: C6 needs
  ≥4 µF **effective** at 5 V bias; C7 must be aluminium electrolytic for its
  ESR; FB1 DCR ≤50 mΩ at ≥1 A.

None of these has a ledger record. They are the genuine Phase 3 scope.

**Next step:** order the boards. Every gate is green — plain DRC 0 violations,
`check_board.py` 12/12, `fab_package.py` ready at 127 of 127, and
`local/fab/caryatid-fab.zip` is current. BT1 is bought separately
(`self-fit.csv`, Digi-Key 3029216).

## 2026-08-23 18:35 — All three orders placed; boards are in fabrication

**Completed:**

- **BOARDS ORDERED.** JLC, five, full turnkey, Economic assembly, top side, ENIG.
  Merchandise $176.24, grand total **$306.95** after $46.97 shipping, $63.21
  customs duties, $1.43 payment fee and $19.10 sales tax. Recorded as
  `JLC-order-2026-08-23`, status `confirmed`, with every form setting captured
  and eight of eight checkable ones verified against the board.
- **Digi-Key ordered**: ten BH-18650-PC-ND at $2.88 and one hundred S9001-ND at
  $0.0247, total **$49.56**. Ten holders rather than five, so five spares.
- **Surface finish changed to ENIG** for about $20, closing
  `hasl-under-fine-pitch`. U1 is a QFN-16 on 0.5 mm pitch with an exposed pad,
  and a no-lead package cannot flex to take up an uneven surface. **The paste
  was deliberately left lead-free**, which is correct for ENIG and would NOT
  have been correct for the leaded HASL revert that was considered and rejected.
- **BT1 fit resolved from MPD's STEP model.** Contacts sit 61.504 mm apart at
  rest with 5.888 mm of travel each, housing wall stops a cell at 70.900 mm.
  Matt's 69.48 mm cell clears the wall by 0.710 mm a side while over-deflecting
  each contact 23% past rating. Seats, under protest.
- **`accessories:` added to lcsc.yaml** as a third sourcing category. Six shunts
  per board were on no bill of materials and no shopping list while
  fab_package.py reported "ready".
- `/bootstrap` Phases 1 and 2, `engagement.yaml` in both repos, caryatid's first
  `CLAUDE.local.md`, `docs/conventions.md`, NGR voice filled, em dash ban made a
  house rule.

**Verified:** plain DRC 0 violations, 0 unconnected, 0 parity; `check_board.py`
12/12; `fab_package.py` ready at 127 of 127. Evidence saved this session:
`2026-08-23-bt1-step-geometry.txt`, `-cost-reconcile.txt`, `-gates-at-order.txt`.

**In flight:** nothing. Three orders placed, all trees clean and pushed.

**Open questions:**

- **`BT1-cell-fit` is `conflict` and stays that way until something is
  assembled.** Geometry says the cell seats; only a holder in hand says it seats
  with sane force and that the contact springs back. **First thing to do when
  the parcels land.**
- **Jumper placement preview** comes through rotated and offset across builds.
  Filed `for-next-time` with three places to look. Not cosmetic: on a 3-pin
  header a 180 degree rotation changes which pair a shunt bridges.
- Confirm Parts Placement, Confirm Production File and Photo Confirmation were
  all off on a first article of 127 placements.
- Tooling holes "Added by JLCPCB" on a fully routed and poured board.
- **Costs were understated by 2.5x for most of this project's life** and the
  cause is now recorded: `cost_estimate.py` models merchandise only. Shipping,
  duties, fees and tax added 74% at JLC and 19% at Digi-Key. Two imports out of
  two carried a tariff and nothing models them.
- Carried: R52/R54 dissipation on a 100 mW 0603, and `MIC_RTN` shared by both
  channels. Both want a capsule measured.
- `docs/values.md` still reasons from a 3000 mAh cell; the ordered cell is
  3400 mAh, so runtime is conservative and charge time is about 13% optimistic.

**Next step:** wait for delivery. On arrival, before building anything, **seat
one Orbtronic cell in one BH-18650-PC** and judge the insertion force and
whether the contact returns. That closes `BT1-cell-fit`. If it does not seat
acceptably, the fallback is a different cell rather than a different holder,
because BT1's footprint is dimensionally specific and swapping it is a board
change.

## 2026-08-23 19:10 — Battery figures regenerated from the cell actually bought

**Completed:**

- **`docs/values.md` regenerated at 3400 mAh.** It had reasoned from a 3000 mAh
  design basis throughout while the ordered cell is the Orbtronic 3400.
  Runtime 12.3 / 7.3 / 5.2 h from 2833 mAh usable, charge 4.0 h at 1 A and 2.7 h
  at 1.5 A, rate 0.29C and 0.44C.
- **The derivation was recovered from the document's own numbers, not assumed.**
  Usable is 83.3% of nameplate and runtime is usable over cell current, which
  reproduces the printed 10.8 / 6.5 / 4.6 h; charge is CC to ~80% then the CV
  tail, which reproduces the printed 3.5 h. Both models validated at 3000 before
  being re-run at 3400. Working in
  `2026-08-23-battery-figures-rederived.txt`.
- **Two further figures were resting on the old capacity**: the A10 gauge
  leakage comparison, 92 mAh over six months, quoted against 3000 mAh in BOTH
  values.md and seed-sheet.md. Both rebased. The 3000 mAh in sourcing.md's
  LiPo-pouch comparison is a different cell and was left alone.
- **`ideocentric/_org.md` gained a costing section** (in ~/.claude, committed
  separately as 42209e1): merchandise is not landed cost, every import so far
  carried a tariff, and read the price ladder at the quantity actually bought.

**Corrected:** I had called the whole 3400 mAh set "conservative" because the
cell is bigger than the design basis. Runtime improved and CHARGE TIME
LENGTHENED. A bigger cell is only conservative in one direction.

**In flight:** nothing. All three orders placed, boards in fabrication.

**Open questions:** unchanged from the previous entry. `BT1-cell-fit` stays
`conflict` until a holder and a cell meet. The jumper placement preview, the
three confirmation steps left off, and JLC's tooling holes are all still open.
R52/R54 dissipation and the shared `MIC_RTN` both still want a capsule measured.

**Next step:** unchanged and physical. On delivery, **seat one Orbtronic cell in
one BH-18650-PC** before building anything, and judge the insertion force and
whether the contact springs back. That closes `BT1-cell-fit`. The fallback is a
different cell rather than a different holder, because BT1's footprint is
dimensionally specific and swapping it is a board change.

## 2026-08-23 19:40 — R52/R54 specified rather than carried

**Completed:**

- **`carbon-capsule-DC-resistance` opened**, `unverified` with an empty evidence
  list because nothing has been measured. It replaces the line carried since
  2026-08-19, "measure a capsule, then decide whether those two want an 0805",
  which never said what reading would mean what. **A carried question with no
  threshold attached cannot be closed by anyone**, which is the same shape as
  the R45 edge-clearance concern that survived four sessions.
- **One number decides it**, the capsule's DC resistance, since it sits in
  series with the 220 ohm resistor across 5 V. `P = (5/(220+Rc))^2 * 220`.
  Below **14.5 ohm** R52/R54 exceed the 100 mW 0603 rating outright and must go
  0805; below **112 ohm** they are inside rating but past a 50% derate, a
  judgement call; above that, nothing to do.
- **The procedure carries its two traps**, both of which would produce a
  confident wrong answer: take several readings while tapping and USE THE
  LOWEST, since granules resettle and lowest is worst case for R52; and measure
  every capsule intended for use, not one representative.
- **The same measurement closes the carried `MIC_RTN` question**: both channels
  on carbon put 31 to 41 mA through the one gated hook switch depending on Rc.
- Noted in the record: the 0.5 V in the existing sourcing.md note is an
  assumption, not a measurement. It implies about 24 ohm, landing in the middle
  band where the answer is a judgement rather than at either end where it would
  be obvious.
- `discovery/README.md`'s entry for the order record was stale, still saying
  "not yet placed".

**In flight:** nothing. Boards in fabrication, all three orders placed.

**Open questions:** five records, two of them open by design.
`BT1-cell-fit` is `conflict` until a holder and a cell meet.
`carbon-capsule-DC-resistance` is `unverified` until a capsule is measured.
Both now say exactly what would close them. Also carried on the order record:
the jumper placement preview, the three confirmation steps left off, and JLC's
tooling holes.

**Next step:** unchanged, and physical, and now there are two of them, both
needing parts in hand. On delivery, **seat one Orbtronic cell in one
BH-18650-PC** and judge insertion force and whether the contact springs back.
Separately, whenever a carbon capsule is to hand, **measure its DC resistance**
against the thresholds above. Neither needs the boards, so the capsule
measurement can happen any time.

## 2026-08-23 20:10 — Cross-repo review: three gaps closed, one of them nine days old

**Completed:**

- **`status.md`'s cost section was stale four ways.** It claimed "$141.36 for 5
  ($28.27/board)... real total ~$159" against actuals of $306.95 to JLC and
  $423.96 all in; said 19 and 20 Extended where the board now has **22**; listed
  `PCB_FAB` as an open placeholder after it was measured at $42.56; and still
  carried the Extended-fee question after it was closed. Both open questions
  struck through with what closed them, and a third added that genuinely is
  live: **nothing models landed cost**.
- **loa's `docs/design/12-phone-build.md` contradicted caryatid AND itself.**
  Last revised 2026-08-11, nine days before ADR 0009. One paragraph said the
  capsule measurement "no longer gates the board, since **the gain stage is DNP
  either way**"; the next said it "gates the board". The first is false: ADR
  0009 populates the front-end at assembly, ADR 0010 cleared every DNP, U4 is
  fitted with both halves live. Corrected, with a dated banner at the top of the
  page because anything else there reasoning from a DNP front-end is stale for
  the same reason.
- **`mic-gain-budget` opened**, `unverified`. audio.md and ADR 0009 both state
  gain targets of ~x3 / ~x100 / ~x1000 and **neither repository contained a
  single capsule output level to derive them from**. ADR 0009 says the capsule
  requirement "was never written down" and calls it a documentation failure
  before a design failure; the same was true one level down, of the levels its
  own targets rest on. This is what Matt could not find at ordering time.

**Verified:** target is the WM8731's own `VINLINE`, **1.0 Vrms at 0 dB**,
extracted with pdftotext from the datasheet rather than a summary and saved as
`2026-08-23-wm8731-line-input-level.txt` because the fetched PDF was in a temp
path. Against class-typical sensitivities, **all three documented targets land
inside their range**: electret needs 56-200x and gets 101x; dynamic needs
250-1000x and gets 1020x with the codec's +12 dB; carbon needs 2-10x and is
passed at 1x with the PGA trimming either way. **The targets were right all
along; what was missing was any way to check them.**

**In flight:** nothing. Six ledger records, both trees clean and pushed.

**Open questions:** three records open, all by design and all stating what would
close them. `BT1-cell-fit` (`conflict`) wants a holder and a cell in the same
hand. `carbon-capsule-DC-resistance` and `mic-gain-budget` (both `unverified`)
want a capsule, and **both close in the same bench session**. Also carried on
the order record: the jumper placement preview, the three confirmation steps
left off, and JLC's tooling holes.

**Next step:** unchanged, and all three open items are physical. On delivery,
**seat one Orbtronic cell in one BH-18650-PC** before building anything.
Whenever a capsule is to hand, **measure its DC resistance** against the 14.5
and 112 ohm thresholds, and **read the op-amp output on a scope** with each gain
leg selected. Neither capsule measurement needs the boards.

## 2026-08-24 — Documentation reframed around who reads it; KiCad stripped two exclusion reasons

**Completed:**

- **`docs/platform.md` written**, the capability specification this repository
  never had. Fifteen documents answered "what is on this board and why we chose
  it"; none answered "should I use it". Leads with the gap the board fills,
  states the support envelope, and carries a limits section written plainly with
  each limit's escape route. Every hard number verified against the board,
  `pins.yaml` or a ledger record before committing: 10 of 10 checks.
- **README reframed.** The first section a stranger met was a warning about
  which git checkout they were in. Reordered around the reader's questions, with
  a one-line pointer keeping the checkout hazard visible to anyone about to
  commit. Status now reads "five ordered, none powered" rather than "fully
  routed", which answers a question someone outside this repo is actually asking.
- **`integration.md` narrowed** to "now that you have decided", losing the
  evaluation material `platform.md` now owns and a stale line about part counts
  being absent until the board was updated.
- **Corrected in `platform.md`:** I wrote the DC input as "5 V nominal". It is
  **5 to 9 V**, never 12, with OVP tripping at 10.2 to 10.8 V. `integration.md`
  had it right and my new document understated the board. Read back from
  `power-sheet.md` rather than reconciled between the two.
- **Standoff guidance reversed.** I had argued for a taller standoff on lip
  clearance; the enclosure record already establishes the board never overlaps
  the lip in plan. Matt's constraint runs the other way: panel pots intrude from
  the lid, so every millimetre of standoff is spent twice. Now says keep it
  short, with the sourcing trap that 4 mm is harder to find than 5 mm, and that
  cable terminations rather than the board usually decide the height.

**Corrected this session, and it is a recurrence worth naming:**

- **KiCad stripped the reasons from two DRC exclusions** when the board was
  opened at 23:49. A1 and A2 kept their exclusions and lost both justifications.
  **The gate does not catch this**: it matches on violation type and item, not on
  the comment, so it reported "0 new, 5 accepted, clean" with two of five excused
  by nobody. Restored with `--apply` in a second; the tool's docstring now says
  to re-run it after any KiCad session.

**Verified:** the board file is untouched at 2026-08-23 10:41, so the design that
was ordered is intact. Only the project file's annotations moved.

**In flight:** nothing. Six ledger records, both trees clean apart from one
untracked file, see below.

**Open questions:** three records open, all stating what closes them, and **two
of the three no longer wait on the boards.** Matt has the telephone in hand, so
the handset capsule can be measured now: DC resistance against the 14.5 and 112
ohm thresholds, and output level against the gain budget. The keypad wants
beeping out before anyone assumes it is discrete rather than a matrix.

**Undecided, and left for Matt:** `hardware/pcb/caryatid-v0.1.pdf`, exported
from KiCad at 23:59 and untracked. **No PDF is tracked anywhere in this
repository** and nothing in `.gitignore` covers it, so it is neither established
convention nor deliberately excluded. It wants a decision rather than a default.

**Next step:** measure the handset capsule. It needs nothing that has not
arrived, it closes two of the three open records, and the thresholds are already
written down.

## 2026-08-24 (later) — PDFs and renders published; a schematic checker, and JP6 fixed

**Completed:**

- **Reference artefacts automated.** `--apply` now writes a composite board PDF
  stacked as the PCB viewer shows it (back copper, front copper, silkscreen on
  top), a six-page schematic PDF, and top and bottom photographic renders at
  `--quality high`. `--archive` copies the PDFs to `discovery/evidence/` under
  dated, SHA-stamped names when an order is placed.
- **Two places, two purposes.** `docs/reference/` and `docs/img/` carry stable
  names and are always current, for reading. `discovery/evidence/` carries
  stamped copies of what was ordered, for provenance. Each artefact is stamped
  by ITS OWN last change: the board and schematic move independently.
- **`check_schematic.py` added**, which reports and never edits. Found JP6 sitting
  in audio.kicad_sch's title block, printing across "File: audio.kicad_sch",
  plus five labels genuinely crossing the resistor they name.
- **JP6 lifted 22.86 mm**, all seven attached elements moved together.

**Corrected, and the checker is the reason:**

- **I claimed twice that labels ran through the resistors**, from a 100 dpi plot
  and then a 300 dpi one. For the short ones they do not: R51's body ends at
  y 132.08 and BIAS_E_L begins at 132.67, clearing by **0.59 mm**. At plot scale
  a sub-millimetre gap reads as contact. The tool now separates OVERLAP, a
  defect, from NEAR, cosmetic, because an eye cannot measure. The longer labels
  do genuinely overlap, so the instinct was half right and only geometry could
  say which half.
- **I nearly shipped a check that fires on healthy work**, reporting "220 of 272
  texts more than 10 mm from their symbol". A reference 10 mm above a resistor
  is correct placement. Dropped rather than reported.
- **A schematic embeds its symbol library beside its placed instances** and the
  two look identical. Matching both reported 49 symbols outside the page
  borders. A placed instance carries `lib_id`; a definition does not. The real
  answer was one.
- **I committed Matt's hand-exported PDF by accident** with `git add -A`, one
  message after saying it was his and I had not touched it. Untracked in
  e6ca99b, history left alone at his instruction, file deleted.

**Verified:** the JP6 move is netlist-identical across 113 nets, ERC 0,
schematic parity 0, board file untouched. Connectivity in a schematic is
positional, so moving the symbol without its three wires and three labels would
have disconnected it silently while still looking right.

**In flight:** nothing. Six ledger records, both trees clean and pushed.

**Open questions:** three records open, two closable with the phone in hand.
Five cosmetic label crossings remain on the schematic; they want a person in
Eeschema, which is the work the checker exists to scope rather than to do.

**Next step:** unchanged. Measure the handset capsule: DC resistance against the
14.5 and 112 ohm thresholds, and output level against the gain budget. Beep out
the keypad at the same time.

## 2026-08-24 20:13 — Schematic legibility closed out: five label crossings and seed's field offset

**Completed:** the two drawing defects `check_schematic.py` was built to scope,
both netlist-verified rather than eyeballed.

- `f249562` — the five labels clipping their resistors (`LEG_101_L/R`,
  `LEG_256_L/R` on audio, `PGOOD_LEG` on seed) moved 2.54 mm out, each with its
  wire's FAR endpoint. The near endpoint is what touches the pin and did not
  move; moving it is precisely how this edit silently changes a netlist.
  Rotating the labels instead was considered and rejected: it clears the body
  but points the text away from the wire it names, trading 0.13 mm of overlap
  for a drawing that reads wrong.
- `ea6cd62` — R11–R18, C8 and C9 on `seed.kicad_sch` reseated from (+6, −30) to
  the (+6, −12) / (+6, −9) the other sheets already use. Sheet median field
  distance 30.59 → 13.42 mm.
- `a5bc7cc` — schematic PDF republished. Only that one artifact was committed:
  the board PDF came back the same byte count differing solely in
  `/CreationDate`, and the two renders differ by raytracer noise, the
  `.kicad_pcb` being untouched. No reason to put 600 kB of that in history.

**A1 and A2 were deliberately left at −30, and that is the finding.** Matt named
seven parts; ten shared the bad offset; two more looked identical to the defect
and were not. The Daisy Seed sockets have a 27.94 mm half-extent, so −30 puts
their fields 2 mm above the body, which is correct. A blanket "move everything
to −12" would have buried both labels inside the socket outline. Symbol extents
come from the embedded `lib_symbols`, per conventions rule 9 — a placed instance
does not record its own size.

**Verified:** netlist identical across `718d5dd..HEAD`, 113 nets and 376 nodes
with the same pins on every one; ERC 0/0/0; parity 0 violations, 0 unconnected
pads, 0 footprint errors; `.kicad_pcb` last changed at `28c54f1` (2026-08-22),
predating every commit under test. Saved as
`2026-08-24-schematic-edits-netlist-identity.txt`. A field carries no
connectivity so none of this *could* have moved a net, but "could not" and "did
not" are different claims and the check costs a second.

**The netlist FILE differs by 144 bytes while the netlist CONTENT does not** —
kicad-cli embeds field positions as symbol properties, so a diff of the file
would have shown a false change. Compare parsed nets, never the raw export.

**My error, and Matt caught it by eye:** I had measured field-to-symbol distance
across all five sheets, got a median of 10.82 mm, called it healthy and dropped
the check. It *was* healthy — for four of them. Aggregating across sheets
drowned a defect that was uniform inside one, where the median was 30.59 mm and
every field exceeded 20 mm. A median over a mixed population hides a uniform
defect in one member of it. The check should have been per-sheet from the start.

**In flight:** nothing. Six ledger records unchanged this session, no fact
touched — this was drawing, not discovery. Both trees clean and pushed.

**Open questions:** three records still open (`bt1-cell-fit` in conflict,
`carbon-capsule-dc-resistance` and `mic-gain-budget` unverified), two of them
closable with the phone in hand and no boards needed. Eight advisory findings
remain in `check_schematic.py`: labels clearing a resistor by 0.59 mm, measured
clear, flagged because they read as touching at plot scale. Cosmetic, and a
judgement call rather than a defect.

**Next step:** unchanged, and now unblocked by nothing at all. Measure the
handset capsule: DC resistance against the 14.5 Ω and 112 Ω thresholds in
`carbon-capsule-dc-resistance`, and output level against the gain budget in
`mic-gain-budget`. Beep out the keypad in the same sitting. That closes two of
the three open records.

## 2026-08-25 12:04 — C21 off the page, and the measurement error underneath it

**Completed:** what Matt reported was one capacitor hanging off a sheet. What it
turned out to be was a text metric that had never been measured, invalidating
every clearance number this project had produced.

- `c831990` — **panel-io's debounce column refitted.** Three identical blocks
  (connector, pull-up, series R, 74HC14 gate, filter cap to ground) repeat every
  59.69 mm at rows 270.51 / 330.20 / 389.89, and A2 is one repeat short. C21's
  lower pin reached 1.48 mm past the frame and the GND flag beneath it sat
  **0.90 mm from the paper edge**. Nothing was wrong with block 3; the pitch was.
  Dropped to 53.34 mm (42 × 1.27), block 1 anchoring, so blocks 2 and 3 rise
  6.35 and 12.70. Bottom-most ink now clears by 3.60 mm. The sheet is on a 1.27
  grid, not 2.54 — the original pitch is 23.5 × 2.54 — and assuming otherwise
  would have thrown the column half a grid out.
- `f0db482` — **20 "advisories" were real collisions.** The checker hedged every
  text overlap as "widths are estimated", and I repeated that hedge back to Matt
  all session as if it meant noise. `VIN_DC` and `PWR_FLAG` share an anchor
  EXACTLY and print as mush. Now graded by interpenetration depth.
- `b86c20b` — PWR_FLAG values hidden, 20 power-symbol texts moved off the
  neighbouring pin rows, **and CHAR_W corrected from 0.72 to 1.17**.
- `365ba12` — 39 label crossings down to 1, in 68 moves across four sheets.
- `8cea8d7` — schematic PDF republished.

**THE CENTRAL FINDING, and it invalidates things I wrote down as fact.** `CHAR_W`
was 0.72 mm per character and carried a comment saying it was measured off a
plot. It was not. Measured at 600 dpi: `'+5V_RAW'` 8.297/7 = 1.185, `'VOUT'`
4.612/4 = 1.153, `'LEG_101_L'` 9.700/9 = 1.078. **A 1.6× underestimate on every
text box in the file.** Consequences:

- `BIAS_E_L` does not clear R51 by 0.59 mm. It runs **3.01 mm into it**.
- The five crossings "fixed" on 2026-08-24 by moving them 2.54 mm were sized
  from this same model, which called a 3 mm overshoot 0.13 mm. **The fix was
  scaled by the error it was correcting**, so it could not have worked.
- Thirty labels crossed, where the tool had reported zero.

A second model error surfaced during the repair: **a label's text direction comes
from `(justify ...)`, not its angle.** `rot 0` and `rot 180` draw identically and
justify decides. The checker derived direction from the angle, so every
horizontal label was modelled on the wrong side of its anchor. The first repair
pass rotated four labels on that model; the plot showed `GAINLEG_L` printed
through C24's `10u`. **That pass was reverted whole and redone from measured
geometry.** The same tool was also using centred boxes for labels in its
text-overlap check and anchored boxes in its crossing check — one label, two
boxes, depending which loop asked.

**The habit that cost this:** the rendered plot showed the crossings correctly at
100 dpi and again at 300, and I overruled it both times with the model, then
wrote the model's answer into `conventions.md` as established fact. A number
feels like evidence and a picture feels like an impression. The plot IS the
artefact being checked; the model is only a claim about it. Rule 3 in
`conventions.md` is now marked REFUTED with the date rather than quietly edited.

**My own errors this session, beyond the above:** I deleted an evidence file as
redundant and restored it (`4bd5375`) — evidence is append-only and pruning it
was mine to propose, not to do. I filtered power symbols by a `power:` lib prefix
and silently skipped three `caryatid:+3V3A` instances, which is exactly the trap
`conventions.md` warns about. And a slice-based self-patch with an empty needle
grew a tool to 17 MB, recoverable only because the file was untracked and cheap
to rewrite.

**Verified:** netlist identical at 113 nets and 376 nodes throughout, ERC 0/0/0,
parity clean, `.kicad_pcb` untouched since `28c54f1` (2026-08-22) — **the boards
on order are unaffected by every commit here.** One proposed move would have
merged `LEG_101_L` into `GAINLEG_L`; the netlist gate caught it and a wire
adjacency check now refuses it a step earlier. Four fixes confirmed on the plot
at 600 dpi rather than in the model.

**In flight:** nothing. Six ledger records unchanged — this was drawing and
tooling, not discovery.

**Open questions:** three records still open (`bt1-cell-fit` in conflict,
`carbon-capsule-dc-resistance` and `mic-gain-budget` unverified), two closable at
the bench. One crossing remains: `AUDIO_OUT_R` against A1 on seed, boxed in on
both sides, and the plot shows the label flags there also overlapping A1's pin
numbers and names — which live in the library definition where no check in this
repo can see them. **That is a known blind spot, not a clean sheet.**

**Next step:** unchanged and still unblocked. Measure the handset capsule: DC
resistance against the 14.5 Ω and 112 Ω thresholds in
`carbon-capsule-dc-resistance`, and output level against the gain budget in
`mic-gain-budget`. Beep out the keypad in the same sitting.

## 2026-08-25 12:29 — Rule 10 written, and the last crossing closed

Short increment on top of the 12:04 entry; three commits.

**Completed:**

- `745bb6e` — **conventions rule 10**, the candidate raised at the previous
  checkpoint: *an empirical constant carries its measurement, or it is a guess
  wearing a lab coat.* Any constant standing in for something physical or
  rendered records the raw observation (what was measured, the sample, the
  number before rounding), because a constant that merely *claims* provenance
  cannot be audited. `CHAR_W = 0.72 # measured off a plot` was not measured, and
  the comment is precisely what let it survive: the line reads as settled. Scope
  is bounded so it does not become a demand to measure grid pitches, which come
  from the file and are exact. It also carries the tie-break: **when a model and
  a rendering disagree, measure the rendering.** Rule 3's REFUTED note now points
  here instead of restating it.
- `be52a15` — **AUDIO_OUT_R cleared, the last of the 39.** Three coordinated
  edits: the `power:GND` at (68.58, 123.19) turned rot 180 → 0, its Value text
  moved 1.27 mm with it, and the label plus its wire moved x 71.12 → 67.31.
  The label is 11 characters like its sibling `AUDIO_OUT_L`, which is anchored
  at 67.31; matching it clears A1 by 1.10 mm and makes the drawing agree with
  itself rather than with a preference.
- `50622bd` — schematic PDF republished.

**A diagnosis I got wrong, and the correction is the useful part.** I called the
GND obstruction a modelling artefact: `lib_extents()` builds a box symmetric
about the origin, and `power:GND` has all its ink on one side of the pin, so it
invents 2.54 mm of empty space. That defect was real and is now fixed
(`lib_box()` / `placed_body()`, asymmetric and rotation-aware, verified against
the plot at angle 0 **and** angle 180). **But fixing it did not dissolve the
obstruction.** That flag is placed at rot 180, so with rotation handled correctly
its ink genuinely occupies 120.65..123.19 — the corridor the label needed. The
symmetric box had been right there for the wrong reason, and the plot agrees:
the triangle measures 120.44..122.13. Being right for the wrong reason is not the
same as being right, and it only showed up because the transform was checked
against a rendering at two angles instead of one.

**A third filter leak.** The crossing check was skipping every `#` reference, the
same filter already pulled out of the border test. A label landing on a ground
flag was invisible to the check whose job it was, which is why the D12/GND-arrow
overlap on panel-io had to be found by a different tool. Removed. With power
symbols now included **and** accurate boxes, the report is identical to the
conservative model: **0 findings either way, across all five sheets.**

**Recorded, not fixed:** a `global_label`'s drawn flag is wider than its text
box, measured 1.18 mm on `AUDIO_OUT_R`. Every box in the checker measures text,
so a label can graze something the check calls clear. Not encoded, because the
overhang is a constant of KiCad's rendering rather than of the file, and guessing
it would be exactly the mistake `CHAR_W` was. Rule 10 applied to itself.

**Verified:** netlist identical at 113 nets, ERC 0/0/0, parity clean,
`.kicad_pcb` untouched since `28c54f1`. On the plot the label's flag now ends at
81.36 against A1's edge at 81.28 and A1's pin number sits clear at 82.63; before
the fix the flags covered the pin numbers outright.

**In flight:** nothing. Six ledger records unchanged; no fact touched.

**Open questions:** three records open (`bt1-cell-fit` conflict,
`carbon-capsule-dc-resistance` and `mic-gain-budget` unverified), two closable at
the bench. Three advisory near-misses remain at 0.50 mm (`SW1_F`/`SW2_F`/`SW3_F`
against R35/R37/R39), which are cosmetic and measured, not defects.

**Next step:** unchanged. Measure the handset capsule: DC resistance against the
14.5 Ω and 112 Ω thresholds, output level against the gain budget, and beep out
the keypad in the same sitting. That closes two of the three open records and
needs no boards.

## 2026-08-25 23:20 — First bench session: the capsule is an electret

The first entry this session that is discovery rather than drawing. Three
commits, and the ledger gained two records.

**Completed:**

- `fb23f51` — **loa's handset transmitter measured and identified: ELECTRET.**
  1.75–1.77 kΩ one probe polarity, 1.05–1.06 kΩ reversed, steady, no jump when
  tapped, measured at the capsule terminals out of circuit. New record
  `loa-handset-capsule`, status `confirmed`.
- `d531d13` — **`mic-configurations.md` gains a fourth branch.** The tree said
  "open circuit → ELECTRET", true only of a bare element, which is a capacitor.
- `5fbc09e` — **`loa-keypad-matrix` created**, saying what to measure before
  anything is measured. Evidence deliberately empty.

**THE IDENTIFICATION RESTS ON POLARITY, NOT MAGNITUDE.** A resistor reads the
same both ways and so does a coil, so an asymmetric reading is a semiconductor
junction and the element is neither carbon nor dynamic whatever band the numbers
fall in. This mattered: the reading matched **none** of the tree's three
branches, so a reader following the documented procedure would have concluded
"not any of these" rather than "electret". The test that actually worked was the
one that does not depend on the number landing where you expected.

**What it closes and what it does not.** Jumpers go to the electret legs, JP1
and JP4 on `1-2`, biased through R51/R53. `carbon-capsule-DC-resistance` stops
being a question about this phone, since R52/R54 only carry capsule current with
a jumper on carbon and an electret never sits across them — but its status is
**unchanged at `unverified`**, because no carbon capsule has been measured and
the record still governs any fitted later. `mic-gain-budget` likewise stays
`unverified`: knowing the type fixes which range applies (56–200×), not whether
the board's ×101 lands inside it, which rests on an unmeasured output level.

**A figure I had to walk back inside a day of writing rule 10.** I computed the
electret bias current as 835 µA from the 1.75 kΩ reading. That is wrong the same
way `values.md`'s 1.5 mA is wrong: `values.md` used 3.3/2k2, treating the capsule
as a short, and I used an ohmmeter reading as an operating resistance. **A JFET
is not a fixed resistor**, and its DC point at 3.3 V is not what a meter probes
at ~0.3 V. The honest statement is a bound: under 1.5 mA per channel, so the
3V3A budget overstates this load by an unknown amount. Closing it needs V across
R51 with the board powered, which is not a bench item. Recorded in the record as
`bias_current_is_bounded_not_measured` so the bound cannot be read as a value.

**Two instrument traps, and they are the same trap.** The capsule terminals were
under hot-melt glue and the first attempts probed through it; glue is an
insulator, so a partial contact reads **high**, and high is the comfortable end
of every threshold in the carbon record. Had this been carbon, probing through
glue could have passed a part that was not safe. The keypad record carries the
matching one before it can bite: the continuity **beeper** is the wrong
instrument, because telephone keypads are conductive rubber on carbon pads that
close at hundreds of ohms to a few kilohm, and a beeper triggering below ~50 Ω
stays silent on a healthy key. **In both cases the instrument's default setting
hides the reading rather than reporting it, and in both cases the failure is
silent and reassuring.**

**In flight:** nothing. Both trees clean and pushed.

**Open questions:** five records open. `bt1-cell-fit` in conflict;
`carbon-capsule-DC-resistance` unverified and now dormant for this phone;
`mic-gain-budget` unverified pending an output level; `loa-keypad-matrix`
unverified pending the bench; a bias-current measurement that needs the boards.

**Next step:** two bench items, neither needing boards. **Capsule output level**
in mV rms at close-talk distance, which is the number `mic-gain-budget` rests
on. And **beep out the keypad** to the template in `loa-keypad-matrix`: twelve
key/pair/resistance rows, the conductor count, and whether any reading changes
with probe polarity. Log the WORST closed resistance, not a typical one.

## 2026-08-31 — loa keypad beeped out: matrix, connector and anchor all closed

**Completed:** `loa-keypad-matrix` goes `unverified` → **`confirmed`**, and
closes three separate questions in one bench session.

- **The matrix is a plain 4×3.** Seven conductors, twelve distinct pairs, four
  rows at three keys each and three columns at four. Closed resistance 10.6 to
  17.5 Ω, worst key `5`, against a 5 kΩ threshold. Clears by two and a half
  orders of magnitude: no pull-down, no stronger drive, no glue logic. loa's
  pin map stands as written.
- **The carbon-pad premise did not hold.** The record warns at length that a
  continuity beeper would stay silent on a healthy key. Every key here is a
  metallic closure near 15 Ω and the beeper would have worked. Warning kept
  verbatim and annotated: it describes a hazard, not this part.
- **The connector is JST ZH 1.5 mm**, refuting the 1.27 mm Molex Picoflex
  derivation of 2026-08-26. The proof is not that a bought ZH stub fitted, it
  is that the whole beep-out ran through it on all seven conductors, which a
  wrong-pitch part cannot do.
- **Pin 1 anchored** to the `PX` silkscreen, with the centring caveat closed by
  observation and a consistency check that passes.
- Evidence: `discovery/evidence/2026-08-31-keypad-matrix-beepout.txt`.
- loa `docs/design/12-phone-build.md` regenerated from the record.

**In flight:** nothing. The sheet is complete and no measurement is outstanding.

**Open questions:**

- **A decision, not a measurement: cross the columns in the harness or in
  firmware.** Rows run straight through to D0–D3. Columns are inverted, and
  reversing three things is swapping the outer two: cross header positions 5
  and 7, leave 6. Or wire straight and reverse the column index in the scan.
  Either is correct. Doing neither shows up as key `1` reading as key `3`.
- Three checks were **not performed** and are logged as not performed rather
  than assumed: the baseline sweep among the four non-black conductors, lead
  and clip resistance, and a polarity reversal for diodes. None changes the
  verdict at a 17.5 Ω worst case against a 5 kΩ threshold.
- The **original ribbon is unexplained** and does not gate anything. Seven
  conductors at 1.5 mm should measure ~10.5 mm overall, not the 9.0 mm
  recorded. Either 9.0 was a centre span or "mass terminated" was mis-observed.

**Why the wrong connector answer survived, worth keeping:** the 9.0 mm reading
fits 1.27 mm as an overall ribbon width (8.89) and 1.5 mm as a pin-centre span
(9.00) equally well, and the datum was never recorded. The 11.5 mm housing
width does discriminate, points at ZH, and was set aside as the inferior
method. The first answer was right and was argued away.

**Next step:** decide the column crossing, then wire a ZH-to-J11 harness and
record the choice under `for_loa_the_build` in `loa-keypad-matrix`.

## 2026-09-20: switch lamp current measured, and the shunt drop that nearly ate it

**Completed:**

- **Bringup A7.6 passed: the switch lamp draws 28.5 mA at 5.00 V**, 5.6 mA at
  3.00 V. 10.2 Ω shunt, Fluke 101 on DC mV, Jesverty supply in CC at a 100 mA
  limit, no board involved. This **closes one of the three unattributed lines
  in the 5 V budget**, leaving the mic bias pair and the three connector 5 V
  pins. Evidence in `2026-09-20-switch-lamp-current.txt`, record updated in
  `panel-latch-switch`.
- **The internal limiting is a plain ~87.5 Ω series resistor, Vf ~2.51 V**, not
  a constant-current driver. Three points fit that model within 1%, the
  residual being the LED's own Vf rising with current. ⇒ **A voltage-range
  marking means the part tolerates the range, not that the current is held
  across it.** Here it tracks the rail almost 8:1 from 3 V to 6 V, so the budget
  line is only meaningful quoted against a rail voltage. That qualifies what
  "internally limited" was taken to promise on 2026-09-05; it does not weaken
  the compatibility pass, which turned on the part tolerating 5 V, and it does.
- **It does not move the runtime table.** 28.5 mA makes the lamp the largest
  indicator load on the rail, ahead of the RGB with all three dies lit, and it
  is lit whenever the instrument is on. But the 150/250/350 mA scenario rows are
  top-down estimates, not a tally: with the lamp in it the tally reaches ~141 mA
  in electret mode and ~163–183 mA in carbon against a 250 mA typical row, so
  the lamp lands **inside** the existing headroom. Runtime figures unchanged.
- **`indicators.md` predicted this correctly and the prediction is now closed.**
  It said, conditionally, that a plain series resistor would give "roughly 75%
  of the current" at 5 V against the 6 V 4×AA reference. It is a plain series
  resistor and the real ratio is 71%. No action, no board change.
- **Five documents corrected off the ledger**, all of which described a 3–9 V
  lamp: `values.md`, `indicators.md`, `sourcing.md`, `power-sheet.md`,
  `capture-checklist.md`. The part in hand is 3–6 V. That discrepancy was
  recorded on 2026-09-06 as "no action"; it became worth fixing once the
  measurement was being written into the same paragraphs.

**🔴 The lesson, and it is a runbook change:** **the shunt drop is not
negligible, and the load never sees the setpoint.** The first reading was taken
at a 5.00 V setpoint, where 258 mV across the shunt left only **4.74 V** on the
lamp, reading **11% low**. It was caught by the numbers not fitting, then fixed
by setting the supply to 5.29 V so the drop left exactly 5.00 V. `bringup.md`
A3 now carries this as a standing warning beside the "do not put the Fluke where
the shunt is" one: add the drop back into the setpoint and re-read, or record
the voltage the load actually saw, but never quote the setpoint.

**In flight:** nothing. No board was powered; this was a component check.

**Open questions:**

- ✅ **Lead resistance: closed the same day, and it was worth the ten seconds.**
  Raised as an open question because clip leads usually run 0.1–0.3 Ω, which
  against the 10.2 Ω shunt would have put every current **2% low**. Probes
  shorted, the Fluke reads **0.0 Ω**, which is a bound rather than a zero: the
  101 resolves 0.1 Ω, so the leads are under ~0.05 Ω, at most 0.5%. **The shunt
  is 10.2 Ω and not a lead-inflated 10.0, so no figure changes and 28.5 mA
  stands.** The least certain term is now the shunt value itself, read at the
  bottom of a 600 Ω range where the meter's "+ N digits" term dominates. A few
  percent, which bounds nothing a budget line cares about.
- The 6.00 V figure of 39.9 mA is **extrapolated**, not measured. It is the top
  of the part's marking and only feeds the brightness comparison.
- **`docs/status.md` still has a RESUME block dated 2026-09-01** that predates
  every component check in Phase A. It is not wrong, but it is drifting, and
  this file has been burned by exactly that before.

**Next step:** the remaining A7 component checks, which are the two LED
questions: **A7.2/A7.4** common anode on J4 and J12 by diode test, and **A7.3**
whether the charge LED's green die is AlGaInP or InGaN, which matters because J4
runs from `VOUT` down to 3.0 V. Then **A7.5**, characterising the test electret
before it is trusted to prove anything else.

## 2026-09-22: handset colour map, transmitter polarity, and a placeholder 7.8x out

**Completed:**

- **loa's handset is fully mapped at the RJ9.** Outer pair **yellow and black**
  is the transmitter, **yellow positive**; inner pair **red and green** is the
  receiver. The 2026-08-25 record established that the *outer pair* was the mic
  but never wrote down which conductors that meant, and 4P4C cord colours denote
  position, not polarity, so there was no convention to fall back on.
- **Polarity settled functionally, not by convention.** Biasing through a
  measured 2174 Ω from 3.3 V: yellow on the resistor gives a **2.882 V** drain at
  **192 µA**; black gives **0.683 V at 1.2 mA**, which is a silicon junction
  forward drop and not an operating point at all. It independently agrees with
  the resistance asymmetry, where the red probe on yellow gave the higher
  reading. Two methods, same answer.
- **The inner pair is symmetric**, 0.821 kΩ both ways. Only one direction was
  taken in 2026-08-25, so nothing had ruled out a second semiconductor there.
- **Corroborates the month-old jack readings to 0.4% and 0.2%** (inner 0.824 →
  0.821, outer 1.054 → 1.056), which also settled that both sets are kilohms.
- 🔴 **The electret bias figure in `values.md` was 7.8× too high.** It carried
  1.5 mA per channel, which is `3.3 V / 2k2`: the current with **the capsule
  treated as a short**. The capsule presents ~15 kΩ at its operating point, so
  the 2k2 drops 0.42 V of 3.3 V. **Measured: 192 µA**, 384 µA for the pair
  rather than 3.0 mA.
- **A trap removed from the runbook.** A6.7 said "electret red to pin 1 or 2,
  black to pin 3", written for the bench capsule. **The handset's red lead is the
  earpiece**, so following it would have wired the receiver into the mic input
  and left the microphone unconnected. A6.7 now names both parts and carries a
  colour table.
- **`values.md` had a second stale bullet**, unrelated to today's reading: the
  mic bias pair was still described as blocked on *measure the handset capsule*,
  a month after the capsule was identified as an electret. The 41 mA carbon
  figure is not live for this build, since JP1/JP4 sit on `1-2` and R52/R54
  never carry capsule current. Corrected and labelled.
- **`mic-gain-budget` gains a quantified lever.** With the operating current
  known, R51 can be sized deliberately: about **13 dB is available at 10k**
  against the 2k2 fitted, before the drain gets tight. Recorded as a lever, not
  a recommendation, since that record is still `unverified`. Also noted that its
  `capsule_output_at_1pa` range carries **no load condition**, which is the
  condition the board's 2k2 would have to be compared against.
- **`bench-instruments` gains the first real check of the ohms function**: a 1%
  2k2 read 2174 Ω, bounding the meter to 0.2-2.2% low on the 6 kΩ range. One
  part at one point is not a calibration and cannot separate meter error from
  part error, and it is recorded as such.

**🔴 The pattern worth keeping:** the record said this measurement **needed the
board**. `what_would_close_it` read "Voltage across R51 with the board powered
... Needs the boards, so it is not a bench item." That is false, and 3.3 V
through a 2k2 into the real capsule *is* R51's circuit. The claim was never
examined; it was assumed because the quantity had been **named after a board
reference designator**. Naming a measurement after the part it will eventually
sit beside is what made it look like it required that part.

**In flight:** nothing. No board was powered.

**Open questions:**

- **A7.5 is still untouched.** This was loa's handset, not the bench reference
  electret, and they are different jobs: the bench capsule's purpose is to prove
  the board, so it still wants characterising before it is trusted.
- **821 Ω at the jack against 145.3 Ω at the element**, on the receiver path,
  now confirmed twice. Roughly 680 Ω sits inside the handset between the two.
  `loa-handset-capsule` says 145.3 Ω is "the figure to use if the receiver is
  ever driven as an output", and **loa will drive it from the RJ9**, where it
  looks like 821 Ω. Not chased: it touches nothing in the mic path.
- The 13 dB R51 ladder **assumes the JFET stays in saturation** as the drain
  comes down. Supported at 2.88 V, unverified below it.

**Next step:** A7.2, A7.3 and A7.4, the three LED checks, all diode-test work on
the bench. Then A7.5.

## 2026-09-22: J4 bicolour verified, and a ticked box that had not been done

**Completed:**

- **A7.2 and A7.3 both pass. The J4 bicolour is verified**, closing an
  `UNVERIFIED` carried in three documents since sourcing. Common anode confirmed
  by diode test; green **Vf 2.322 V** at 5 V and **2.234 V** at 3 V, red 1.862
  and 1.810. New ledger record `j4-charge-led`, since neither LED had one.
- **The green die is AlGaInP**, 0.7 V clear of the InGaN true green at 3.0-3.2 V
  that would have disqualified it. This was the whole question, because J4 hangs
  on `VOUT` and not a regulated rail. **It still lights at a 3.00 V supply**, at
  0.77 mA, which is the flat-cell acceptance test `sourcing.md` asked for.
- **A second, independent confirmation came free.** The diode test *lit the green
  die*. A handheld supplies only ~2.4 V on that range and cannot light a 3.0 V
  InGaN part, so A7.2 corroborated A7.3 before any voltage was read.
- 🔴 **This measurement is the only information that exists about the part.** The
  Amazon listing was never readable, so nothing was ever quoted from the vendor:
  not the forward voltages, not the package, not the pinout. `datasheets.md` now
  says the question was closed by measurement because that was the only way it
  could be closed.

**🔴 New finding, which nothing in the documents anticipated: the amber drifts
toward red as the cell drains.** Green's higher forward voltage eats
proportionally more of a shrinking headroom, so green fades 2.4× across the
cell's life while red fades 2.0×, and the red-to-green current ratio goes from
**1.25 on a full cell to 1.55 on a flat one**. Two consequences: the R9/R10 trim
is **not a fixed adjustment**, so trim at mid-cell rather than on a freshly
charged pack; and **resistors cannot fully fix it**, because it is driven by the
Vf difference against a falling rail, not by the resistor ratio. Harmless, and
arguably it reads correctly. Recorded so it is not rediscovered as a fault. It
was only visible because the part was measured at **both ends** of the rail,
which is exactly what `sourcing.md` asked for: "Test it at 3.0 V, not 4.2 V."

**🔴 A ticked checkbox that had not been done.** `capture-checklist.md` carried
*"[x] ~~Measure the RGB forward voltages and confirm common anode.~~ **Done**"*
with Vf figures against it. Those figures are **the vendor's specification**,
quoted as such in `sourcing.md` under "Specification from the vendor". Reading a
listing is not measuring a part, and the checkbox said *Measure*. **Unticked**,
with the reason written in, and A7.4 stands as genuinely outstanding. This is
the same failure the project keeps catching: a vendor claim hardening into a
measured fact through repetition, here through a tick.

**A trap in A7.4 itself, recorded before anyone hits it:** a handheld's diode
test supplies only ~2.4 V, so the RGB's **3.0-3.2 V green and blue dies will read
OL even when good and correctly oriented**. A7.2 and A7.4 both say "diode test",
and followed literally that produces "green is dead". Use the bench supply
through a series resistor. The J4 part was measurable on diode test only because
its green turned out to be 2.322 V.

**Corrections off the ledger:** `indicators.md` said "2.1 mA per die" from an
assumed 2.1 V green; measured it is **1.88 mA**, ~10% optimistic, and the 4.2 mA
amber total survived by accident since red's surplus covers green's shortfall.
`sourcing.md`, `status.md` and `datasheets.md` all carried the part as
unverified.

**In flight:** nothing. No board was powered.

**Open questions:**

- **Diffused is untested on the J4 part**, and it is a *visual* check, not an
  electrical one. Both dies lit together must give one amber lens, not a red dot
  beside a green dot.
- **Legibility at 3.0 V is also unjudged.** The meter proves 0.77 mA flows; it
  does not prove the LED can be *read* on a flat cell, which is the actual
  requirement.
- **A7.4, the RGB, is not started**, and its checkbox is now correctly unticked.
- **A7.5, the bench reference electret, is still untouched.**

**Next step:** A7.4 on the four-pin RGB, using the supply rather than the diode
test, then the two visual checks on the J4 part. Then A7.5.

## 2026-09-23: A7.4 done, and two corrections in the same direction

**Completed:**

- **A7.4 passes.** RGB is **common anode** (diode test, red probe on the common
  pin) and **diffused**. Vf at 5 V: red 1.932, green 2.454, blue 2.607, through a
  measured 990 Ω. New ledger record `j12-rgb-led`. **The J4 bicolour is diffused
  too**, closing the fourth and last of `sourcing.md`'s requirements for it, and
  the only one a meter could not settle.
- **The part-identity question dissolved.** `sourcing.md` records CHANZON
  `B01C19ENFK` and then says to buy the diffused AliExpress version "at the same
  specification", so which listing supplied the part was unknown. **The bag label
  reads R 2.0-2.2 V and G/B 3.0-3.2 V, which is the spec the repo already
  carried.** Whichever listing it came from, the recorded figures describe what
  is in hand.
- **A7.2/A7.3/A7.4 are all now complete**, plus both visual checks.

**🔴 Two claims withdrawn, both mine, both the same error.**

The bag labels read 3.0-3.2 V for *both* greens, which contradicted two things
written into the ledger and six documents on 2026-09-22:

1. *"The J4 green die is AlGaInP, 0.7 V clear of InGaN."*
2. *"The RGB's vendor spec is wrong by 0.4 V on green and blue."*

**Both rested on extrapolating a logarithmic diode fit from two low-current
points out to the 20 mA rating.** A log-only fit omits series resistance, which
for an InGaN die is 10-30 Ω: it contributes a linear IR term that dominates at
20 mA and is invisible at 2 mA. Restore it and the measurements agree with the
labels. **The labels are probably right.**

The stated validation was wrong too. The argument was that red landing inside
the vendor band proved the method sound. **It proves it for red alone**, red
being the low-series-resistance case that was never in doubt. A check that only
passes on the case not in question is not a check.

**A7.3 still passes, and the reason matters.** It never depended on the
chemistry. The real question was measured directly: **green lights at a 3.00 V
supply through 990 Ω, drawing 0.77 mA.** That is J4's circuit at the cell's end
of life, at the operating point, with no model. *A directly measured operating
point survived; an inferred material property did not.* The runbook's A7.3 has
been rewritten from "is the die AlGaInP" to "does the green still light on a
flat cell", because the original phrasing invited exactly this. The amber-drift
finding is unaffected, for the same reason.

**🔴 And the same error was already in `values.md`, pointing the other way.**
Its "the RGB cannot be driven from a 3V3 GPIO" table **uses forward voltages
quoted at 20 mA to reason about a circuit that would run at one or two
milliamps**. At the real operating point green gets ~2.2 mA and blue ~1.7 mA,
dim but not the "0.45 mA and 0.15 mA, invisible, no resistor value fixes it"
that is written there. **The decision stands** (an STM32 sinks harder than it
sources, the 5 V rail is stiffer, currents are defined); the argument does not.

**An LED's Vf is not a constant, and a datasheet figure carries its test current
with it.** That is the durable lesson, and it caught two documents and me.

**In flight:** nothing. No board powered.

**Open questions:**

- **The green dies' chemistry is unresolved and deliberately left so.** Settle
  it, if ever worth it, at **20 mA in CC**, the label's own condition, with no
  resistor and no extrapolation. It does not gate anything: J12 runs from 5 V
  with headroom either way, and J4 was settled functionally.
- **`values.md` and `sourcing.md` disagree on the RGB currents** and did before
  any of this: 5.9/6.7/6.3 against 4.80-5.20/4.83-5.50. They differ on whether
  to allow the GPIO's 0.35 V output-low drop. Both defensible, one should be
  picked. Not resolved.
- **Legibility of the J4 green at 3.0 V** is still a judgement by eye, not made.
- **A7.5, the bench reference electret, remains untouched.**

**Next step:** A7.5, which is the last A7 item and the one the runbook says to do
first, since it is the reference everything in Stage 8 leans on.

## 2026-09-23 (evening): the supply was lying, the label was right, and one mistake explains everything

**Completed:**

- 🔴 **The bench supply's CC is offset by +3.53 mA with unity gain.** Set 2 / 5 /
  10 mA delivers **5.98 / 8.53 / 13.53 mA**, and the 5-to-10 pair gives a slope
  of **exactly 1.000**. Two permanent consequences: **it cannot deliver below
  ~3.5 mA in CC whatever you set**, and **a wanted current must be set 3.5 mA
  low**. The floor is soft, not sharp: the 2 mA point ran +0.45 mA high and
  wandered 5.2-6.8 mA. This closes the `minimum settable current limit` item
  that `bench-instruments` has carried since the supply arrived.
- **That explains the anomaly that started it.** The green read 2.54-2.59 V at a
  *set* 2 mA against 2.454 V at 2.57 mA under CV: voltage up as current down,
  which a diode cannot do. **It was never at 2 mA, it was at about 6.** One LED,
  no unit variation, nothing wrong with either reading.
- **The green chemistry is settled at rated current: Vf 2.844 V at 18.15 mA**,
  extrapolating to ~2.87 V at 20 mA. An AlGaInP green would read 2.50-2.65 V
  here. **It is InGaN and the bag label is right** to within about 0.13 V.
- **The meter's ohms gain error is now a figure, not a bound: ~1.1% low across
  two ranges**, from three parts landing within **0.18% of each other**. It is
  the tightness that is the evidence. Implies the 10.2 Ω shunt is nearer 10.31
  and every current derived from it is ~1.1% low: the switch lamp becomes
  28.2 mA rather than 28.5. Inside the few percent already recorded, so nothing
  moves, but the caveat is closed.

**The scorecard on my own claim, at 20 mA:**

| | |
| --- | --- |
| 2026-09-22 claim | 2.66 V, **wrong, 0.21 V low** |
| measured | **~2.87 V** |
| bag label | 3.0-3.2 V, ~0.13 V high |

The withdrawal was correct. The claim was wrong in method *and* in number, and
the kernel it contained, that the label is slightly optimistic, is a **third**
the size claimed and changes nothing.

⚠️ **Even the corrected fit was optimistic.** Six points predicted 2.894 V at
this current against a measured 2.844, a **50 mV** miss where every earlier
point landed within 8 mV. The curve flattens at the top more than the model
expects. **Extrapolation remains the weak step even after the missing physics is
put back**, which is the second time in two days it has been the thing that
failed.

**🔴 One mistake explains all of it.** `values.md`'s 3V3 table, both documents'
RGB current tables, and my withdrawn claim are the *same error*: **a forward
voltage used at a current other than the one it was quoted at.** Vf is not a
constant, and a datasheet figure carries its test current with it.

That also **resolves the `values.md` / `sourcing.md` disagreement** flagged
yesterday. Recomputed from measured Vf at the current each channel actually
converges to:

| die | measured | `values.md` | `sourcing.md` |
| --- | --- | --- | --- |
| red | ~5.2 mA | 5.9 ✗ | 4.80-5.20 ✅ |
| green | ~6.8 mA | 6.7 ✅ | 4.83-5.50 ✗ |
| blue | ~6.4 mA | 6.3 ✅ | 4.83-5.50 ✗ |

**Neither document is right about all three.** `values.md` is right on green and
blue *by cancellation*, having omitted the 0.35 V sink drop as well, and high on
red. `sourcing.md` is right on red and low on the other two. Being right for the
wrong reason is not being right. Both tables corrected, and `sourcing.md` now
carries two Vf columns so the distinction cannot be lost again.

**J4 returns to `confirmed`.** The conflict was between my claim and the label;
my claim is dead on independent evidence. ⚠️ **That part's own green was not
re-measured**, so its chemistry stays *unmeasured* rather than inferred by
analogy from a different part. It gates nothing: A7.3 passed functionally.

**In flight:** nothing. No board powered.

**Open questions:**

- **The J4 green's chemistry is unmeasured** and deliberately not inferred.
- The supply's **set resolution and published accuracy** are still unread; only
  the listing title was ever retrieved.
- **Legibility of the J4 green at 3.0 V** remains a judgement by eye, not made.
- **A7.5, the bench reference electret, is still untouched** and is now the only
  outstanding A7 item.

**Next step:** A7.5. Note the new constraint when planning it: **use CV with a
measured series resistor, not CC**, for any current below about 20 mA.

## 2026-09-23 01:18: checkpoint. Four A7 component checks closed, two instrument errors quantified, three of my own claims withdrawn

**Completed:**

- **`panel-latch-switch`** A7.6. Switch lamp **28.5 mA at 5.00 V**, 5.6 mA at
  3.00 V. Internal limiting is a plain ~87.5 Ω resistor, Vf ~2.51 V, not a
  current source, so the current tracks the rail ~8:1 across the 3-6 V marking.
  Closed one of three unattributed lines in the 5 V budget. Lead resistance
  measured 0.0 Ω the same day, closing its own caveat.
- **`loa-handset-capsule`**. RJ9 colour map settled: outer **yellow/black** is
  the transmitter with **yellow positive**, inner **red/green** the receiver,
  symmetric. Polarity established functionally, not by convention. Electret
  operating current **192 µA**, replacing a derived 1.5 mA that was **7.8×**
  high. The record's claim that this needed the board was false and is annotated.
- **`j4-charge-led`** (new) A7.2, A7.3. Common anode, diffused, and the green
  lights on a flat cell at **0.77 mA from a 3.00 V supply**. Closed an
  `UNVERIFIED` carried in three documents since sourcing. New finding: **the
  amber drifts toward red as the cell drains**, ratio 1.25 → 1.55, so the
  R9/R10 trim is not a fixed adjustment and resistors cannot fully fix it.
- **`j12-rgb-led`** (new) A7.4. Common anode, diffused, Vf **2.844 V at
  18.15 mA** → InGaN, bag label right to ~0.13 V. Resolved the standing
  `values.md`/`sourcing.md` current disagreement: red ~5.2, green ~6.8, blue
  ~6.4 mA, and **neither document was right about all three**.
- **`bench-instruments`**. Supply CC is **offset +3.53 mA at unity gain**, so it
  cannot deliver below ~3.5 mA and a wanted current must be set 3.5 mA low.
  Meter ohms **gain error ~1.1% low across two ranges**, from three parts within
  0.18% of each other.
- **`mic-gain-budget`**. R51 quantified as a lever: ~**13 dB** available at 10k.
  Stays `unverified`; the SPL assumption and capsule output are still unmeasured.
- **Three claims of mine withdrawn**, all one error: *a forward voltage used at
  a current other than the one it was quoted at*. The same error was already in
  `values.md`'s 3V3 table and both RGB current tables.
- **Documents corrected off the ledger**: `values.md`, `indicators.md`,
  `sourcing.md`, `power-sheet.md`, `capture-checklist.md`, `datasheets.md`,
  `status.md`, `bringup.md`. A7.3 rewritten from "is the die AlGaInP" to "does
  the green still light on a flat cell", because the original phrasing invited
  the error. `capture-checklist.md`'s RGB item was unticked (it recorded a
  vendor spec as a measurement) and re-ticked once actually done.

**In flight:** nothing. No board was powered at any point this session; every
measurement was a component on the bench.

**Open questions:**

- **A7.5, the bench reference electret, is untouched** and is the only
  outstanding A7 item. New constraint from tonight: use **CV with a measured
  series resistor, not CC**, for any current below ~20 mA.
- **The J4 green's chemistry is unmeasured**, deliberately not inferred by
  analogy from the RGB. It gates nothing.
- **Legibility of the J4 green at 3.0 V** is a judgement by eye, not made.
- **Receiver reads 821 Ω at the RJ9 against 145.3 Ω at the element**, confirmed
  twice. ~680 Ω sits inside the handset. Matters only if the receiver is ever
  driven as an output, which loa would do from the RJ9.
- The supply's **set resolution and published accuracy** are still unread.
- `docs/status.md` still carries a **RESUME block dated 2026-09-01** predating
  every Phase A component check.
- Pre-existing and untouched this session: **`loa-hook-switch`** and
  **`charger-input-voltage-thermal`** are both `in-progress`.

**Next step:** Run **A7.5**. Characterise the bench test electret before it is
trusted: DC resistance across its two pigtails **both ways**, expecting a finite
kΩ that differs by direction (the integral JFET), per
`discovery/findings/bench-test-electret.yaml`. Then confirm polarity by biasing
it through a measured ~2k2 from 3.3 V in **CV** and reading the drain voltage,
the same rig that gave the handset capsule 192 µA. No board required.

## 2026-09-23: A7.5 closed, and all six A7 checks are done

**Completed:**

- **`bench-test-electret` goes `unverified` → `confirmed`**, closing A7.5 and
  with it **every A7 component check**. Nothing in Phase A's component list is
  outstanding, and no board was powered to get there.
- 🔴 **There are two bench capsules, not one.** The record described a single
  article. In hand: the **small pigtailed B0FRLZLH2G** it describes, and the
  **uxcell B01F5592EO**, which this record had said *"DO NOT BUY IT"*. It was
  bought anyway. **The verdict's reasoning is untouched**: both are bare
  two-terminal electrets, identical on the axis that decides correctness, and
  pigtails beat pads on a bench. One thing it did not anticipate, in mild
  qualification: **a second independent article separates a board fault from a
  capsule fault at E8**, which one capsule cannot do.
- **Test A, both capsules pass.** Small 1.397 k / 1.154 k, large 1.286 k /
  0.828 k. Finite kilohms, clearly asymmetric, so both are electrets with an
  integral FET. ⚠️ The large one's readings are **unattributed**: no colour, no
  longer lead, so the magnitudes are recorded without knowing which pad the red
  probe sat on.
- **Test B on the small capsule, in R51's own circuit.** 3.30 V through a
  measured 2174 Ω: **drain 2.558 V, 339 µA**, CV confirmed at 3.301.
  **Red is positive**, by measurement rather than convention.
- **One reading settled the polarity and the reverse was not needed.** A
  forward-biased junction at 339 µA would sit near 0.6 V, not 2.558. The
  handset needed its reverse taken because the failure mode there was a 0.683 V
  junction drop that had to be seen; here the working orientation was hit first
  and is unambiguous alone.
- **The resistance test predicted the polarity, two for two.** Meter red on the
  positive terminal gave the higher reading on both the handset (yellow,
  1.798 k) and this capsule (red, 1.397 k), each confirmed functionally
  afterwards. Recorded **with its sample size**: two is a prior that has paid
  off twice, not a law.
- **The large capsule's negative pad is identified but not measured.** Matt
  spotted metal legs running from one pad to the capsule body, which is the can
  bond and makes that pad negative. Logged as an observation, not a reading.

**🔴 What "proved" means here, stated in the runbook so nobody arrives at E8
believing otherwise.** A7.5 established four things: that it is genuinely an
electret, which lead is positive, its operating point, and a baseline. **It did
not establish that the capsule produces usable signal.** That needs the board or
a scope, the bench cannot answer it, and no claim is made.

**Also:** 339 µA does **not** go into `values.md`. That budget line stays at
192 µA because the **handset capsule is what ships**; the bench electret never
leaves the bench. Putting it in the budget would be the same class of error as a
datasheet figure quoted at the wrong condition.

**In flight:** nothing. No board powered.

**Open questions:**

- **The large capsule's can bond is unconfirmed.** Ten seconds with the meter:
  probe each pad to the can rim, the legged one should read near 0 Ω. It would
  also **attribute** its Test A readings, and it predicts meter-red on the
  non-legged pad gives the higher 1.286 k, making the polarity rule three for
  three.
- The large capsule has **never been biased** and needs leads soldered first.
- **J4 green's chemistry** unmeasured; **J4 green legibility at 3.0 V** unjudged.
- Receiver reads **821 Ω at the RJ9 against 145.3 Ω at the element**.
- `docs/status.md` **RESUME block still dated 2026-09-01**, now a full phase of
  component checks out of date.
- Pre-existing, untouched: `loa-hook-switch` and `charger-input-voltage-thermal`
  are both `in-progress`.

**Next step:** Phase A's component work is finished, so the next move is a
decision rather than a measurement: **update `docs/status.md`'s RESUME block**,
which is the first thing read when picking this project up cold and now predates
every A7 result. Then Phase B, the first board checks, which is where a board
gets powered for the first time.
