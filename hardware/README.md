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

**Board outline: 47.8 × 98.6 mm**, matching absonus. Grow only if layout proves
it necessary, and grow outward from the hole pattern rather than moving it.

**Mounting holes: four M3, on a 40.64 × 91.44 mm pattern inherited from
absonus.** That is exactly **1.600″ × 3.600″** — round imperial, chosen
deliberately over there, and worth keeping for a reason beyond continuity:

> Same outline and same hole pattern means **the boards are mechanically
> interchangeable.** An absonus enclosure can take a caryatid board. A spare
> shell fits either. Standoffs, drill templates and panel jigs are shared.

**Fix the pattern now and never move it.** It is the one dimension three
enclosures all have to agree on, and it costs nothing today against redrilling
later.

**Four layers, not two.** This is a density decision and a noise decision, and
they point the same way. Counting the real part list — 89 passives, four ICs, the
Seed sockets and eighteen connectors — a 2-layer board at realistic density is
about **120% full** at the absonus size and needs roughly +50% area to breathe.
At four layers it is **72% full at the absonus size**, which is comfortable.

The noise argument is the stronger one. The layout rules call for **one unbroken
ground plane**, and on two layers that is aspirational — the plane is cut to
ribbons by the traces that have nowhere else to go. With inner planes for ground
and the rails, the boost's switching return stays local by construction instead of
by careful placement, and the analogue bus gets a quiet reference underneath it.

**The perimeter is the real constraint, not the area.** Eighteen connectors want
roughly 200 mm of board edge against a 293 mm perimeter — about **69%** — before
mounting holes, edge keep-out and cable exits. Vertical JSTs can sit inboard
where a cable can still reach them, which is the relief valve, but connector
placement should be planned before anything else is placed rather than fitted
around the ICs afterwards.

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