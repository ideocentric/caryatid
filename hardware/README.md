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

## Assembly split

- **JLC SMT, single side** — charger, boost, filtering, all passives including
  the DNP-optional networks. Order DNP parts as explicit "do not place" lines.
- **Hand** — IDC headers, all JSTs, Seed headers.