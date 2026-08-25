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
