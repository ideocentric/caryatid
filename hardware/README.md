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

**Board outline: 65 × 115 mm**, a starting target for layout to trim rather than
a fixed edge. absonus is 47.8 × 98.6; this is bigger because caryatid carries
about four times the part count and an on-board cell.

**It has to clear the small BUD enclosure** with the 4×AA caddy removed — that
space is what pays for the increase. Check the internal dimensions before the
edge cuts are drawn; it is the only enclosure constraint that binds.

**Two layers.** Density says four would be easier, but width is cheaper than
layers here and the enclosure has the room. At 65 × 115 the component area comes
to about **64% fill** before the cell, which leaves a ground pour that is
actually continuous rather than nominally so.

**Put the SMD and the battery holder on opposite faces.** This is what makes two
layers work at this size. All SMD on one side, the holder and every through-hole
connector on the other, so the copper *under the cell* is still usable instead of
15 cm² of dead board. It also keeps SMT to a single side, which is the cheaper
assembly.

**On-board 18650 holder.** Soldered rather than a pack tacked into the enclosure,
which removes the last hand-crimped power loom — and with it the reverse-polarity
risk that had no protection behind it. A holder cannot be wired backwards.

**Keep J2 as well, and populate one or the other.** A remote pack stays possible
for an enclosure that wants the weight somewhere else, which is the freedom the
platform exists to preserve. **Silkscreen "HOLDER *or* J2 — not both"**: a cell in
the holder and a pack on J2 are two cells in parallel.

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
end, and battery polarity at J2. This board is assembled once and cabled many
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

**DNP stops being advisory.** When the connectors were hand-fitted, "DNP" meant
*don't bother*. Now it is an instruction JLC acts on and bills for, so a wrong
DNP line is either a connector you paid for and did not want or one you needed
and did not get.

**Through-hole assembly needs the Standard service**, not Economic, and is
priced per joint so it scales with connector count in a way SMD placement does
not. absonus was ordered that way deliberately — the cost is accepted in exchange
for an empty hand-solder list.