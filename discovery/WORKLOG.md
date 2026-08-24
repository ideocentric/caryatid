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
