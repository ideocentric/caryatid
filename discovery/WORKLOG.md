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
