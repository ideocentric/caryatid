# Seed sheet

Every connection on `hardware/pcb/seed.kicad_sch`: the module and its sockets,
the two analogue measurement networks, and the rails.

## The symbols

**`Daisy_Seed_Socket_A` and `Daisy_Seed_Socket_B`** in `caryatid.kicad_sym` —
pins 1–20 and 21–40. Placed side by side they read as the Seed, with the pins
fanning outward the way the two socket rows sit on the board.

They replace a single 40-pin `Daisy_Seed_Rev4` symbol, which is in the git
history but no longer in the library. One symbol is one designator is one
footprint, so it could not produce the two socket BOM lines the board needs —
see [Sockets](#sockets--they-have-their-own-designators) below. Three things
about them are deliberate.

**Pin names are the Electro-Smith silkscreen** — `D0`–`D30`, with the analogue
pins as `A0/D15` and so on — not the peripheral names a stock symbol uses
(`SD_DATA_3`, `ADC_INP10`, `SPI1_NSS`). The frozen map speaks silkscreen, so the
symbol does too, and cross-checking the schematic against
[pinmap.md](pinmap.md) stays mechanical instead of requiring a translation
table in someone's head.

**Pin numbers were cross-checked between two independent sources**: libDaisy's
`doc/Daisy_Seed_Rev4_Pinout.csv` and the symbol embedded in the fabricated
absonus board. All forty positions agree. The absonus symbol names them by
peripheral function, which is why it was not simply reused.

**The part each symbol stands for is the socket, not the module.** The pins are
named for the Seed because that is what makes the schematic readable, but the
BOM line is a 1×20 female socket and the Seed is bought separately. This is why
the symbols carry `Reference = A` and land as `A1` and `A2`.

## Name every Seed net after its pin

`D0` is a net called `D0`. `A7` is a net called `A7`.

This is the point of a frozen map. It makes the netlist and `pinmap.md`
directly comparable — the cross-check in the capture checklist becomes a
diff rather than an act of interpretation — and it means the `A?`/`A??` net
class patterns catch the analogue nets automatically.

The panel sheet knows `D7` is the hook switch; the net does not need to say so.
Put that in a text annotation, not in the net name.

## Rails

| Pin | Name | Net | Note |
| --- | --- | --- | --- |
| 39 | `VIN` | `+5V` | from the boost, through the ferrite |
| 40 | `GND` | `GND` | |
| 20 | `AGND` | **`GND`** | one plane — see below |
| 21 | `3v3A` | `+3V3A` | analogue rail: J5 pot tops, J9, J10 |
| 38 | `3v3D` | `+3V3` | digital rail: J11, comms ports, A11 encoder |

**`AGND` ties to `GND`.** The platform layout rules call for one unbroken ground
plane and no split, so the Seed's analogue ground returns to the same copper.
Noise is controlled by placement — keeping the boost's switching loop small and
its return currents local — rather than by cutting the plane. A split plane with
a single stitch is a longer return path pretending to be isolation.

`3v3A` and `3v3D` do stay separate, because those are supplies rather than
returns and the Seed generates them separately.

## Battery gauge — A10

Pin 32, `A10/D25`.

| Component | From | To |
| --- | --- | --- |
| R11 100 kΩ | `VBAT` | `A10_DIV` |
| R12 100 kΩ | `A10_DIV` | `GND` |
| R13 1 kΩ | `A10_DIV` | `A10` (pin 32) |
| C8 10 nF | `A10` | `GND` |

Divides by two: 4.2 V reads 2.10 V, 3.0 V reads 1.50 V — comfortably inside the
ADC range with room at both ends.

**This draws ~21 µA continuously, including while the instrument is off** —
about 0.5 mAh a day, 92 mAh over six months. Acceptable against 3000 mAh, and it
is the one thing on the board that never stops. If that ever matters, the fix is
a MOSFET in the divider leg, not larger resistors: raising them past 100 kΩ
starts to fight the ADC's input impedance.

## Charge-status code — A11

Pin 35, `A11/D28`. Four resistors of one value — the 0.1% 10 kΩ already in
stock, C374544.

| Component | From | To |
| --- | --- | --- |
| R14 10 kΩ | `+3V3` | `A11_DIV` |
| R15 10 kΩ | `A11_DIV` | `~{CHG}` |
| R16 10 kΩ | `A11_DIV` | R17 |
| R17 10 kΩ | R16 | `~{PGOOD}` |
| R18 1 kΩ | `A11_DIV` | `A11` (pin 35) |
| C9 10 nF | `A11` | `GND` |

R16 and R17 in series make the 20 kΩ leg. Derivation and the four resulting
levels are in [indicators.md](indicators.md); why one value rather than three is
in [sourcing.md](sourcing.md).

`~{CHG}` and `~{PGOOD}` arrive as hierarchical labels from the power sheet.

**The pull-up is on `+3V3`, not `VOUT`** — so the network draws nothing while the
instrument is off, unlike the battery gauge above.

## Everything else

Every remaining Seed pin leaves as a global label named for the pin.

| Pins | Net names | Goes to |
| --- | --- | --- |
| 1–15 | `D0`–`D14` | panel-io |
| 16–19 | `AUDIO_IN_L`, `AUDIO_IN_R`, `AUDIO_OUT_L`, `AUDIO_OUT_R` | audio |
| 22–31 | `A0`–`A9` | panel-io |
| 33, 34, 36 | `D26`, `D27`, `D29` | panel-io — RGB |
| 37 | `D30` | panel-io — expansion CS |

**No pin is unused.** D0–D30 is 31 pins, plus four audio and five power, which
is the whole forty. There are no no-connects on this sheet, and if ERC reports
one, something is missing rather than intentionally absent.

## The DACs are spent, and that is worth knowing

`A7/D22` is `DAC1_OUT2` and `A8/D23` is `DAC1_OUT1`. caryatid uses both as
analogue panel inputs on J5.

Using them as ADC inputs is fine — they are ADC-capable and the DAC peripheral
simply stays disabled — and this board makes audio through the WM8731 codec, not
the MCU DACs. But **a future instrument wanting CV or gate outputs will find its
DAC pins occupied by potentiometers**, and freeing one means giving up an
analogue panel channel. Recorded here so that discovery happens now rather than
during a board spin.

## Sockets — they have their own designators

The Seed sits on **two 1×20 female sockets, 40 pins total**. `C2897383` is the
part absonus used; `C41361038` is the equivalent sitting in the JLC inventory.
Machine-fitted, per the assembly split.

**This is where the absonus order went wrong, and it is worth not repeating.**
absonus carried a single designator `A1` — the Daisy Seed symbol, present only to
get the footprint right — so the BOM asked for **one** socket where the board
physically needs **two**, and the quantity had to be corrected by hand at order
time.

**The two strips have separate designators**, `A1` and `A2`, each with its own
1×20 socket footprint. The BOM quantity is right because the schematic says so,
rather than because somebody remembered.

The Daisy Seed module itself is **not a BOM line** — it is bought separately and
pushed into the sockets.

### Orientation must be drawn back in

Two plain socket rows lose what the single Daisy Seed footprint was quietly
providing: **which way round the module goes.** Inserted backwards, `VIN` lands
on a GPIO and `GND` on something that is not ground, which destroys the module,
the board, or both.

The footprint was carrying that information as silkscreen, so splitting it means
putting the silkscreen back deliberately. **This is built** —
`caryatid:DaisySeed_Socket_A_1x20` and `_B_1x20` carry all of it:

- **Module outline** — a rectangle showing the Seed's body, so it is obvious the
  two rows are one part.
- **`USB` legend at the pin 1 end.** This is the orientation cue that matters;
  everything else is decoration.

  Pin 1 and pin 40 sit at that same end, so there are two independent landmarks
  to check a physical module against: **the USB connector is at the `D0` /
  `GND` end**, opposite the `AGND` / `3v3A` end where pins 20 and 21 are. In the
  schematic symbol that is the top.

  **Verified against a third source**, not just the pinout CSV and the absonus
  board: KiCad's stock `Module:Electrosmith_Daisy_Seed` silkscreen carries an
  8 mm connector tab protruding past the body, centred on the module axis, at
  the pin-1/pin-40 end — with the pin-1 chamfer at that same end.
- **Pin-1 marker**: a dot at `A1` pin 1, plus a **square pad at the USB end of
  both rows** — `A1` pin 1 and `A2` pin 40. Two landmarks, one per strip.

**No per-pin labels.** An earlier version of this document called for printing
`D0`, `D7`, `A0`, `VIN` beside all forty pins, on the grounds that the frozen map
would become visible on the copper. That was drawn and then removed: a label
that only restates the pin name still leaves you tracing the net to learn
anything, so it earns very little for forty pieces of silkscreen.

It also did not survive contact with the fab. At 2.54 mm pitch the labels only
fitted at 0.7 mm, which is **below JLCPCB's 0.8 mm floor** — they would have
printed blurred or been dropped. Growing them to a legible size ran the longer
names (`AUDIO OUT L`) into J11's pads.

**The orientation cue is the marking that earns its space**, because it prevents
an error rather than describing one.

**The risk this would have introduced is designed out.** Loose board graphics
stay behind when a socket moves, so none of this is loose: every line and label
lives inside the two footprints and travels with them.

The remaining exposure is the two strips being placed at the wrong spacing, and
that is made self-evident rather than left to a review step — **the module
outline and the USB tab are split on the centreline**, half on each footprint.
At exactly 15.24 mm apart they close up into one rectangle and one tab. At
anything else the outline is visibly broken.

Socket height is one of the four measurements that set the panel standoff, with
the switch bezel, the jack barrels and the IDC headers. **Measure before any
footprint is placed.**