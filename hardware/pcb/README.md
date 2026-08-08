# PCB

Empty. The KiCad project goes here.

Expected structure — hierarchical sheets, so the power section stays a reusable
block for any future board that outgrows this one:

```
pcb/
  absonus-platform.kicad_pro
  absonus-platform.kicad_sch    root
  power.kicad_sch               charger, boost, latch, charge LEDs
  seed.kicad_sch                Seed headers, battery gauge, charge-status code
  audio.kicad_sch               jacks, coupling, optional mic bias
  panel-io.kicad_sch            analogue bus, digital bus, switches, comms ports
  absonus-platform.kicad_sym    project-local symbols
  absonus-platform.pretty/      project-local footprints
  absonus-platform.kicad_jobset fabrication output job
```

Target: KiCad 8 or newer, two layers, 1.6 mm.

**Do not start schematic capture until [ADR 0006](../../docs/decisions/0006-licensing-is-open.md)
is answered.** Whether this design derives from Adafruit's reference schematics
or is drawn from the TI datasheets decides the licence, and deriving cannot be
undone after the fact.

## Before any footprint is placed

Buy and measure the mechanical parts. Switch bezel diameter, jack barrel length,
IDC header height and Seed header height together set the panel standoff height,
and that number has to exist before placement rather than after.

The illuminated latching switch is the one to measure first: its Ø12/Ø16/Ø19
bezel fixes the panel hole, and its lamp current confirms `R_LED` is genuinely a
0 Ω link at 5.2 V.