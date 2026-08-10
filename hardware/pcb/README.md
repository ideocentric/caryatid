# PCB

KiCad 9 project. **All four sheets are captured.** 125 components, 101 nets,
**ERC clean at 0 violations.**

| Sheet | State | Check |
| --- | --- | --- |
| `power.kicad_sch` | 27 components, 19 nets | netlist diffed node-by-node against [power-sheet.md](../../docs/power-sheet.md); `ITERM` the one deliberate no-connect |
| `seed.kicad_sch` | 12 components | all **31** physical pins in `pins.yaml` land on a net named after the pin |
| `panel-io.kicad_sch` | 46 components | all **29** pins declaring a connector reach it, traversing series R and the debouncer |
| `audio.kicad_sch` | 35 placements, 28 DNP | 17 nets diffed against [audio.md](../../docs/audio.md), including `C_g` in series with `R_g` |

**The dangling-global count reached zero.** It ran 33 → 4 → 0 as seed, panel-io
and audio landed, and each drop was predicted before the sheet was drawn. Five
no-connects remain and all five are deliberate: `ITERM` on the charger, `J11`
pin 9 (the spare), and the three unused 74HC14 outputs.

Treat any *new* ERC message as real. The design now has nothing expected to be
wrong, so there is no noise for a fault to hide in.

Placement is functional rather than tidy — components on a 1.27 mm grid with
labelled stubs, meant to be dragged into shape in the GUI. The bootstrap scripts
in [`tools/oneshot/`](../../tools/oneshot/) are spent; do not re-run them.

```
pcb/
  caryatid.kicad_pro       project: net classes, design rules, sheet index
  caryatid.kicad_sch       root — four hierarchical sheets, nothing else
  power.kicad_sch          charger, boost, latch, hardware charge LEDs
  seed.kicad_sch           Seed headers, battery gauge, charge-status code
  audio.kicad_sch          jacks, coupling, mic bias / preamp / pad options
  panel-io.kicad_sch       analogue bus, digital bus, switches, comms ports
  caryatid.kicad_sym       symbols: BQ24074RGT, TPS61023DRL, Seed sockets A/B
  caryatid.pretty/         footprints: BQ24074 QFN, Seed sockets A/B
  sym-lib-table            so the project libs resolve without global config
  fp-lib-table
```

Open `caryatid.kicad_pro`. `caryatid.kicad_pcb` carries **all 125 footprints,
placed and net-bound**, on a 100 × 90 mm outline with four M3 holes. **Nothing is
routed** — DRC's 263 unconnected items are the full ratsnest, which is correct.

Placement is a machine first pass, not layout. It puts each block where the
zoning says and nothing overhangs the outline, but ~33 courtyards still overlap
and the silkscreen is a mess. Treat it as something to drag from.

## Which face

**Front:** BT1, both Seed sockets, and every through-hole connector — 21 parts.
**Back:** all 104 SMD, classified by each footprint's own `attr`, not by name.

This is the checklist's "SMD on one face, holder and through-hole connectors on
the other", and it pays immediately: `courtyards_overlap` went from 33 to **zero**,
because SMD and through-hole can no longer collide.

The flip is stored the way KiCad stores it, checked against a KiCad-written
board rather than assumed: back-side footprints hold **Y-negated** coordinates,
F/B layer names swapped, and `(justify mirror)` on every text. Arcs survive
because KiCad 7+ stores start/mid/end and all three mirror together.

**Two things to confirm before ordering.**

`J13A` is the SMD Qwiic socket, so it classified as SMD and went to the back.
Electrically fine; whether you want a Qwiic cable leaving from the underside is
a mechanical question, not one the classifier can answer.

**Through-hole bodies are on the front, so their pins protrude into the SMD
side.** JLC cannot wave-solder them from the back without hitting SMD. For small
runs their through-hole work is hand soldering, which is probably fine — but you
asked for the JSTs to be machine-fitted as on absonus, and absonus had a
component-free underside. Worth putting to JLC before the order.

## The connector ring

Placed by function, and stacked from measured courtyard extents rather than by
hand — hand arithmetic on offsets produced touching parts three times running.

| Edge | Connectors |
| --- | --- |
| Left | `J1` DC in, `J2` remote battery, `J3` latch switch, `J4` charge LEDs |
| Left, inboard | `J11` digital bus IDC, beside A1 (the digital row) |
| Right | `J12` RGB, `J9` soft pot, `J10` FSR, `J17` audio out |
| Right, inboard | `J5` analogue bus IDC beside A2; `J16` expansion; `J18` audio in and `J14` mic return together |
| Bottom | `J6` `J7` `J8` switches, then `J13B` and `J15` module ports |

Power enters on the left where the charger and boost sit underneath; the
analogue bus, both sensors and the audio pair are on the right, furthest from
L1. `J18` and `J14` are adjacent because they are one loom — capsule signal and
its bias return to the hook switch's second pole.

**Everything is at rotation 0.** A vertical JST exits upward, so turning the pin
row to follow the edge buys nothing — and the rotated-courtyard transform is the
one piece of geometry here that could not be checked against a known-good file,
so it is not used. If you rotate parts by hand in the GUI, KiCad does that
arithmetic correctly.

**The four M3 holes are part of the collision check.** They were not, at first,
and that version passed a board where `J6` and `J18` each sat on top of a
mounting hole. They come from the skeleton rather than from the netlist, which
is exactly why a check built around the component list missed them.

## How dense is it, really

| | mm² |
| --- | --- |
| All 125 courtyards | 4510 |
| of which BT1 | 1774 |
| everything except BT1 | **2736** |
| board | 9000 |
| face left after BT1 | 7226 |

**38% coverage on BT1's face**, which is at the top of the comfortable band for
two layers but inside it. An earlier read of this said the board was "essentially
full"; that was wrong, and it was wrong for an instructive reason — the figure
came from a packer that added 1.6 mm around every part, which inflates an 0603
courtyard nearly six-fold. Measure coverage from courtyards, not from packing
margins.

What *is* tight is the connector ring. The edge connectors are 920 mm² of the
2736 and they all want board edge, which no rectangular zoning expresses. That
is the part worth doing by hand first.

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

**Local labels are sheet-qualified, and that defeats a bare pattern.** A power
symbol makes a global net called `VBAT`; a *local* label on the power sheet makes
a net called `/power/SW`. The pattern `SW` does not match `/power/SW`, so the
boost switching node — 1.51 A peak — would have silently fallen into Default.
The pattern is therefore `/power/SW`, spelled out. Any future HighCurrent or
Analog net carried on a local label needs the same treatment; global labels and
power symbols do not.

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

## Footprints — checked against the stock libraries

Every footprint named in `sourcing.md` resolves in KiCad 9's stock libraries,
including the four JST XH ones that were assumed by naming convention rather
than verified. Two need a project-local variant, and both are already built.

**`caryatid:BQ24074RGT_QFN-16-1EP_3x3mm_P0.5mm`** — because **none** of the five
stock QFN-16 3×3 footprints put any paste on the exposed pad; every one is
`F.Cu`/`F.Mask` only. Derived from `EP1.7x1.7mm_ThermalVias` with a 2×2 aperture
array at 72% coverage. EP is 1.68 ±0.07 per SLUS810N drawing 4222419/E, so 1.7 is
inside tolerance.

**Thermal vias are 0.3 mm drill on 0.55 mm pads at ±0.5 mm.** TI's drawing calls
for Ø0.2 mm, which is below JLC's 0.3 mm minimum hole; and at TI's ±0.6 position
a 0.55 mm pad leaves only 0.176 mm to the signal pads. Moving them inboard to
±0.5 gives 0.289 mm and satisfies both.

**The exposed pad is 1.68 mm, TI's nominal.** It was briefly 1.70 — inherited
from the stock footprint that had a ThermalVias sibling — which lands *exactly*
on the 0.2 mm clearance boundary and fails on rounding.

Two caveats worth carrying into layout and into the order:

- **The four thermal vias sit under the paste apertures and must be tented.** On
  a 1.68 mm pad the vias and the apertures both want the corners; making them
  disjoint drops coverage to 45%. This is a via setting, not a footprint fix.
- The only package drawing in the datasheet is **RGT0016C**, while Table 7-1
  lists the '74 as **RGT0016B**. TI did not publish the B drawing. If the two
  differ, the EP dimension is what changes.

**`caryatid:DaisySeed_Socket_A_1x20` / `_B_1x20`** — two 1×20 socket rows so the
BOM asks for two sockets from the schematic. They carry the module outline,
pin-1 dot, square pads at the USB end of both rows and the `USB` legend, split on
the centreline so wrong spacing shows as a broken outline. Per-pin labels were
drawn and dropped — see [`docs/seed-sheet.md`](../../docs/seed-sheet.md).

## Silkscreen: JLCPCB's numbers

| | Absolute minimum | Recommended |
| --- | --- | --- |
| Character height | **0.8 mm** | ≥ 1.0 mm |
| Line width | **0.15 mm** | ≥ 0.2 mm |
| Pad-to-silk clearance | — | ≥ 0.25 mm |

Two project rules were looser than that and have been tightened:
`min_text_thickness` 0.08 → **0.15**, and `min_silk_clearance` 0 → **0.25**,
which was disabled entirely. `min_text_height` was already correct at 0.8.

Expect the silk-overlap count to *rise* after that change. It is not a
regression — the rule was previously not checking.

**BT1 is settled and needs no project-local work**: MPD `BH-18650-PC`,
`C5339083`, on stock `Battery:BatteryHolder_MPD_BH-18650-PC`, whose pads match
the drawing exactly (72.90 mm terminals, 55.61 mm mounting holes). It is rated
for protected cells, which was the open question. The Keystone 1042 was rejected
— 87.9 mm of courtyard against the MPD's 79.2 mm.