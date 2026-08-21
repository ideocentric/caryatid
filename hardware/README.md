# Hardware

Empty. The KiCad project lands in [`pcb/`](pcb/) once the licence question in
[ADR 0006](../docs/decisions/0006-licensing-is-open.md) is answered — that
answer decides whether schematic capture may start from an Adafruit source file,
and it cannot be revisited afterwards.

## What will be committed

The editable design:

- `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`
- project-local symbol and footprint libraries
- STEP exports alongside any native mechanical CAD

## What will not

Anything regenerable: gerbers, drill files, pick-and-place, fabrication
archives. A gerber directory in the tree drifts from the board file within about
two revisions and then quietly misleads whoever trusts it. Released fabrication
output belongs on a tagged release, so a given release maps to exactly one set
of files that were actually ordered.

## Design intent

[`docs/pinmap.md`](../docs/pinmap.md) is the source of truth for pin
assignment and is generated from `docs/pins.yaml`. The schematic follows it, not
the other way round.

Layout rules are inherited from the platform spec and are frozen with the board:

1. **Zones** — charger and barrel jack on one edge, boost in the corner beyond
   it, Seed centre, audio jacks on the opposite edge. Analogue IDC near the
   Seed's analogue row, digital IDC near its digital row.
2. **One unbroken ground plane.** No split AGND/DGND planes. Control noise by
   placement: keep the boost switching loop small so its return currents stay
   local.
3. Wiper RC filters at J5; 100 Ω series at J11.
4. No switcher traces under or parallel to audio nets or the analogue bus.
5. Enclosure bonds to ground at **one point**, at or near the audio jacks.
6. Ferrite and bulk between the boost and everything downstream.
7. Route the RGB lines away from the analogue bus — status changes are edges too.

## Mechanical and fabrication

None of this was specified before and all of it is needed before layout.

**Board outline: 150 × 90 mm.** absonus is 47.8 × 98.6; this is bigger because
caryatid carries roughly four times the part count and an on-board cell.

The BUD's internal is **178 × 110 mm, measured** (2026-08-18) — against a
catalogue internal of 107.9 × 177.8, which was near enough exact. The
**95.2 × 165.1 mm** "usable rectangle", derived by taking 0.5″ off each axis for
the sloped sides, under-read the real box by 12.9 and 14.8 mm and **is
retired**. 150 × 90 sits inside the measured floor with 28 mm of length and
20 mm of width to spare.

That slack is **not** centred. The board mounts 5 mm from the left wall, hard
against the 5 mm screw columns, reserving all 28 mm at the right — the latching
power button is long and needs it, and the device is held in the left hand, so
the board's mass belongs over the supporting hand rather than cantilevered out
to the right. Facts and provenance:
[`discovery/findings/bud-cu477-interior.yaml`](../discovery/findings/bud-cu477-interior.yaml).

**The 100 mm rule is retired.** It claimed JLCPCB's cheapest tier is 100 × 100 and
that crossing it costs money for nothing. The tier is real, but the cost of
crossing it was never checked and turns out to be small — so the rule was
protecting against a number nobody had measured. See
[ADR 0008](../docs/decisions/0008-board-outline-and-layer-count.md).

**Two layers.** Density says four would be easier, but width is cheaper than
layers and the enclosure has the room. At 90 × 100 the component area is about
**53% fill** before the cell, which leaves a ground pour that is genuinely
continuous rather than nominally so, and slack for a 2-layer router.

**Put the SMD and the battery holder on opposite faces.** This is what makes two
layers work at this size. All SMD on one side, the holder and every through-hole
connector on the other, so the copper *under the cell* is still usable instead of
15 cm² of dead board. It also keeps SMT to a single side, which is the cheaper
assembly.

**On-board 18650 holder.** Soldered rather than a pack tacked into the enclosure,
which removes the last hand-crimped power loom — and with it the reverse-polarity
risk that had no protection behind it. A holder cannot be wired backwards.

**There is no remote-pack connector.** J2 carried that option until layout, and
was removed: no instrument on the platform asked for it, and it was the only way
a reversed cell could reach the charger, which has no reverse protection. A cell
now reaches the board only through a soldered holder, which cannot be wired
backwards.

**The holder must take a protected cell.** Those are ~69 mm against the 65 mm
most holders are cut for. Check the part before ordering, or the cell will not
seat.

**Mounting holes: four M3, inset from the corners, pattern fixed once the outline
is.** absonus's 40.64 × 91.44 mm (1.6″ × 3.6″) pattern is **not** being retained —
the current absonus uses standard batteries with a panel cutout, so there is no
interchangeability to preserve and no reason to inherit its geometry.

**Test points.** Bring-up needs `VBAT`, `VOUT`, `+5V`, `+3V3`, `+3V3A` and
several `GND`, as real pads rather than "somewhere to hook a probe". A board
whose connectors are all populated and whose looms are not yet made has nowhere
convenient to measure otherwise.

**Fiducials.** Three, on the top layer, for machine placement — the QFN-16 and
the SOT-563 are both 0.5 mm pitch, which is where placement accuracy starts to
matter. Confirm JLC's current requirement rather than assuming three is right.

**Silkscreen carries the wiring.** See [connectors.md](../docs/connectors.md):
every connector's pin functions and pin 1, the Seed pin names, `USB` at the pin 1
end. This board is assembled once and cabled many
times, so the board itself should be readable without the documents.

## Assembly split

**JLCPCB fits everything, including the through-hole parts.** absonus was built
this way — its BOM carries the JST-XH connectors, the 2×5 IDC header, a DIP and a
radial electrolytic alongside the SMD — so the precedent and the part numbers are
both proven.

- **SMD** — charger, boost, 74HC14, MCP6002, all passives.
- **Through-hole** — every JST, both IDC headers, the Seed sockets, the barrel
  jack, the expansion header.
- **Hand** — nothing, by intent.

Two consequences that follow from this and are easy to miss.

**DNP stopped being advisory, and then stopped existing.** When the connectors
were hand-fitted, "DNP" meant *don't bother*. Once JLC fits the through-hole
parts it is an instruction they act on and bill for, so a wrong DNP line is
either a connector you paid for and did not want or one you needed and did not
get — and which one it is only becomes clear when the boards land.

[ADR 0010](../docs/decisions/0010-nothing-is-dnp.md) took the count to **zero**.
Every symbol is assembled; the options that used to be DNP are now selected by
jumper after assembly, or were `open` positions that no supplier could ship and
have been deleted. BT1 is the only part the assembler does not fit, and it is
**not** DNP — it is self-fit from Digi-Key, which `lcsc.yaml` records and
`fab_package.py` acts on.

**Through-hole assembly needs the Standard service**, not Economic, and is
priced per joint so it scales with connector count in a way SMD placement does
not. absonus was ordered that way deliberately — the cost is accepted in exchange
for an empty hand-solder list.