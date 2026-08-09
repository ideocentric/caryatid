# PCB

KiCad 9 project. **Skeleton in place, no schematic content yet.**

```
pcb/
  caryatid.kicad_pro       project: net classes, design rules, sheet index
  caryatid.kicad_sch       root — four hierarchical sheets, nothing else
  power.kicad_sch          charger, boost, latch, hardware charge LEDs
  seed.kicad_sch           Seed headers, battery gauge, charge-status code
  audio.kicad_sch          jacks, coupling, mic bias / preamp / pad options
  panel-io.kicad_sch       analogue bus, digital bus, switches, comms ports
  caryatid.kicad_sym       project-local symbols (empty)
  caryatid.pretty/         project-local footprints (empty)
  sym-lib-table            so the project libs resolve without global config
  fp-lib-table
```

Open `caryatid.kicad_pro`. **There is no `.kicad_pcb`** — KiCad creates it the
first time the board editor is opened, and a hand-written one would carry no
information a fresh file does not.

Verified with `kicad-cli` rather than assumed: ERC runs clean and traverses all
four child sheets, and a netlist export resolves the full hierarchy.

```sh
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$KCLI" sch erc --output erc.rpt caryatid.kicad_sch
```

## Net classes

Set in the project file, with pattern assignment so nets land in the right class
as they are named rather than by hand afterwards.

| Class | Track | Clearance | Via | Applies to |
| --- | --- | --- | --- | --- |
| Default | 0.25 mm | 0.2 mm | 0.6 / 0.3 | everything else |
| Power | 0.8 mm | 0.25 mm | 0.8 / 0.4 | `+3V3`, `+3V3A`, `+5V` |
| HighCurrent | 1.2 mm | 0.3 mm | 1.0 / 0.5 | `VBAT`, `VOUT`, `VIN_DC`, `SW` |
| Analog | 0.3 mm | 0.25 mm | 0.6 / 0.3 | `A?`, `A??`, `AUDIO_*` |

`HighCurrent` is the one that matters. The cell delivers over an amp at low state
of charge and takes 1.29 A back while charging, and `SW` carries the boost's
switching current — 1.51 A peak at worst case. Those are not signal nets.

**Name the nets to match the patterns.** A net called `BAT+` will land in
Default and be routed at 0.25 mm, which is how a board gets warm.

## Design rules

Set conservatively against JLCPCB's capabilities rather than at them: 0.2 mm
minimum track and clearance, 0.5 mm minimum via with a 0.3 mm hole. JLC will
accept finer, but a first spin is not the place to spend that margin.

**Two layers, 1.6 mm, 90 × 100 mm.** Inside JLCPCB's 100 × 100 price tier and
inside the BUD's 95.2 × 165.1 mm usable rectangle. **Neither edge goes past
100 mm** — crossing that costs money for nothing.

## Before capture

Work down [`../../docs/capture-checklist.md`](../../docs/capture-checklist.md).
The parts of it that gate everything else:

- **[ADR 0006](../../docs/decisions/0006-licensing-is-open.md) says draw from the
  TI datasheets.** No Adafruit schematic is opened during this work — deriving
  cannot be undone afterwards.
- **The pin map is frozen.** [`docs/pinmap.md`](../../docs/pinmap.md) is
  generated from `docs/pins.yaml`, and the schematic is a consumer of it, not a
  second opinion. Label Seed nets with pin names (`A7`, `D11`), not with what
  they happen to do on one instrument.
- **Three measurements still outstanding** — the handset capsule, the switch lamp
  current, and the mechanical parts that set panel standoff height. The first
  gates the audio sheet; the third gates any footprint placement.

Values are in [`docs/values.md`](../../docs/values.md), part numbers and
footprints in [`docs/sourcing.md`](../../docs/sourcing.md). Several absonus
footprints are reusable as-is, which turns a chunk of this into transcription.