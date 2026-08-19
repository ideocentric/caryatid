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
