# 8. Board outline and layer count

Date: 2026-08-10

## Status

Accepted. Supersedes the undocumented 90 × 100 decision and the "neither edge
past 100 mm" rule.

## Context

The outline and layer count were settled early in three commits over about
thirteen minutes — `91a0556` (four layers, absonus outline), `ac6d02b` (two
layers, 65 × 115), `d4b1fec` (90 × 100) — and **never written up**, despite
[ADR 0001](0001-record-architecture-decisions.md) saying a decision belongs here
if reversing it would cost a board spin. This one would.

Three of the premises turned out not to hold.

**The price tier was never priced.** "JLCPCB's cheapest board tier is 100 × 100;
past it, price scales with area" appears in three documents and is sourced in
none. Priced properly, going to 100 × 200 turned out to be a small increase — so
the rule that shaped the outline was protecting against a cost nobody had
measured.

**The four-layer case was half answered.** `91a0556` argued two things: density
("two layers is about 120% full at this size") and plane integrity ("the layout
rules already demand one unbroken ground plane, and on two layers that is
aspirational: the plane gets cut to ribbons by traces with nowhere else to go").
The density half was answered by growing the board — the 120% was measured at the
old 47.8 × 98.6 outline. **The plane-integrity half was never addressed.**

**The two-layer preference was inherited from a project that no longer describes
this board.** It comes from loa's [ADR 0002](../../../loa/docs/decisions/0002-daisy-seed-as-compute-platform.md),
whose reasoning is hand-solderability. caryatid is fully machine-assembled with a
0.5 mm-pitch QFN and a SOT-563; its own README says "**Hand** — nothing, by
intent."

## Decision

**150 × 90 mm, two layers.**

The growth is entirely on the long axis, where the conservative BUD working
rectangle leaves 15 mm spare at 150 mm. **The 90 mm axis is unchanged** because it
is the one proven to fit, and the alternative — 100 mm — relies on a STEP reading
of ~110 mm that is explicitly marked indicative and has never been checked against
the physical box.

| | area | coverage | perimeter | connector ring |
| --- | --- | --- | --- | --- |
| 90 × 100 (was) | 9000 | 50.1% | 380 mm | 53% |
| **150 × 90** | **13500** | **33.4%** | **480 mm** | **42%** |

The perimeter number matters as much as the area: `91a0556` identified **the
perimeter, not the area, as the binding constraint** — eighteen connectors want
about 200 mm of edge.

**Two layers is retained**, on the basis that the growth answers the plane
argument as well as the density one: more room means fewer signals forced through
the F.Cu pour. This is the premise to revisit if routing proves it wrong, and it
is now written down so that revisiting it is a decision rather than a rediscovery.

**The "neither edge past 100 mm" rule is retired.** It was a proxy for a price
that was never checked.

## Consequences

- The CU-477 drill pattern changes from 90 × 80 mm to **140 × 80 mm** — X ±40,
  Z ±70 in the STEP frame. `docs/sourcing.md` carries the numbers.
- **The standoff is 2 mm.** Every component sits on the front and the back is
  bare copper, so the standoff only clears solder joints. This reverses the
  SMD-to-back flip: that was right at 90 × 100, where the copper under the cell
  was worth reclaiming, but the enclosure is shallow and C7 at 5.4 mm cannot hang
  underneath. Single-sided SMT is also the cheaper assembly, and it leaves B.Cu
  free as a routing layer. Stack is ~25 mm, not ~30.
- Placement was redone. The schematic, symbols, footprints and BOM are unaffected
  — this is an outline change only.
- 150 mm exceeds the JLC 100 × 100 tier deliberately. **100 × 200 was also
  considered and rejected**: it does not fit the BUD, and
  [ADR 0002](0002-one-board-many-instruments.md) requires one layout to serve
  absonus and baby borg as well as loa.
- **Both enclosure floors have since been checked, and 150 × 90 clears both**
  (2026-08-11, after this decision was accepted):

  | enclosure | usable floor | margin at 150 × 90 |
  | --- | --- | --- |
  | BUD CU-477, conservative | 95.2 × 165.1 | +5.2 short / +15.1 long |
  | BUD CU-477, STEP interior | ~110 × 170 | +20 / +20 |
  | telephone shell | 152.4 × 101.6 (6″ × 4″) | 5.8 mm per side / 1.2 mm per end |

  The phone's 6 × 4 figure **already reserves ≥ 6.35 mm on every side**, so the
  true clearance there is ~12.1 mm per side and ~7.5 mm per end. The 1.2 mm is
  spare inside a rectangle that is itself derated — not a 1.2 mm gap to a wall.

- **Height clears too, and the BUD is the binding case** — not the phone:

  | | interior height | headroom at 26.91 mm stack |
  | --- | --- | --- |
  | telephone shell | > 40 mm | > 13 mm |
  | **BUD CU-477** | **34.14 mm** | **7.23 mm** |

  The BUD figure is **derived from the STEP, not measured**: 38.10 mm external
  (1.500″) with a 1.98 mm wall given independently by the base and the cover,
  reconciling exactly. A plane 1.60 mm proud of the floor would reduce headroom to
  5.63 mm if the standoffs seat on it. Confirm with calipers.

- **The standoff is 4 mm as built, not 2 mm.** 2 mm is the *electrical* minimum
  that follows from the front-side flip — the back face is bare, so the standoff
  only has to clear solder joints — and it was recorded above as though it were
  the build spec. It is not. 4 mm is the mechanical choice, it costs 2 mm of
  headroom, and the BUD has room for it. `tools/check_board.py` uses 2 mm because
  the check it performs is the electrical one.

- No enclosure dimension is open any more. The cell stays on the board, so **J2
  does not come back** — the `VBAT` connector was removed as the last path by
  which a reversed cell could reach an unprotected charger input, and nothing now
  requires restoring it.