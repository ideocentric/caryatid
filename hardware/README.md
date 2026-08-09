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

**Mounting holes.** Four, M3 clearance (3.2 mm), one per corner, with keep-out
for the standoff shoulder. The board is held on M3 standoffs inside whatever
enclosure an instrument uses, so the hole pattern is the one thing every shell
has to match — **fix it early and do not move it**, or three enclosures need
redrilling.

**Board outline.** Not yet decided, and it is now the gating item for layout
rather than standoff height. The constraint that binds is loa's: **the board has
to fit inside a telephone shell.** Measure the cavity before drawing the edge
cuts. absonus and baby borg have roomier enclosures and will not be the limit.

**Clearance above the board** is 10.5 mm, set by a 1×20 socket at 8.5 mm plus the
Seed sitting on it. The 2×5 IDC box headers are close behind at about 9 mm.
Nothing else comes near.

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