# Sourcing

What is already in the JLCPCB library and on the absonus board, and what caryatid
still needs. Component *values* are in [values.md](values.md); this is about part
numbers, footprints and what is physically in stock.

Drawn from the JLC parts inventory and the absonus working BOM. **The footprint
names are the most useful thing here** — they are already drawn, already
fabricated once, and reusing them turns capture into transcription.

## Already in the library

| LCSC | Part | Footprint | Stock | For |
| --- | --- | --- | --- | --- |
| **C4749194** | DS254P-2X5-L0 | `IDC-Header_2x05_P2.54mm_Vertical` | **176** | J5, J11 |
| **C374544** | AR03BTDX1002A010, 10 kΩ **±0.1%** | 0603 | **176** | A11 divider — see below |
| **C41361038** | DS1023-1x20S21 | `插件,P=2.54mm` | **36** | Seed sockets, 2 per board |
| C158012 | JST **B2B-XH-A(LF)(SN)**, 2-pin | `JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical` | on absonus | J2, J6, J7, J8, J10 |
| C144394 | JST **B3B-XH-A(LF)(SN)**, 3-pin | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | on absonus | J9 |
| C160404 | JST-SH 4-pin horizontal | `JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` | on absonus | **J13a, Qwiic** |
| ~~C5289485~~ | ~~LS18-P~~ | — | on absonus | **superseded** by the 74HC14, [ADR 0007](decisions/0007-rc-and-schmitt-instead-of-the-ls18-p.md) |
| C2897383 | Daisy Seed Rev4 | `Electrosmith_Daisy_Seed` | on absonus | the module outline |
| C3337 | 220 µF electrolytic | `CP_Elec_5x5.4` | on absonus | bulk |
| C15401 | 10 kΩ 1% | 0603 | on absonus | general |
| C4211 | 3 kΩ | 0603 | on absonus | was the absonus soft-pot pulldown |
| C188666 | **6N138SDM** optoisolator | SOP-8-2.54mm | 0 | **MIDI breakout, not this board** |

Two notes on that list. The 2×5 IDC at 176 covers J5 and J11 for about eighty
boards, and the Seed sockets at 36 cover eighteen. And the **6N138 is already
identified** — it is the MIDI input opto, and it belongs on the daughterboard,
not here, exactly as [ADR 0003](decisions/0003-comms-ports-are-protocol-agnostic.md)
says.

*(The two inventory exports supplied are byte-identical — a duplicate download,
not two different lists.)*

## Standardise the JSTs on XH

absonus uses **JST-XH, 2.5 mm** throughout, and Qwiic SH only where the Qwiic
standard requires it. caryatid's spec said JST-PH for the battery and left the
rest generic. **Follow absonus: XH everywhere except J13a.**

One crimp tool, one housing family, one set of pre-crimped leads, and two of the
sizes are already stocked. It also happens to be the better electrical choice for
the battery: **XH is rated 3 A against PH's 2 A**, and this board pulls over 1 A
from the cell at low state of charge and can push 1.29 A into it while charging.
PH would have been working close to its rating for no reason.

| Connector | Size | Have it? |
| --- | --- | --- |
| J2 battery, J6/J7/J8 switches, J10 FSR | XH 2 | ✅ C158012 |
| J9 soft pot | XH 3 | ✅ C144394 |
| J3 latch, J4 charge LEDs, J12 RGB | XH 4 | ✅ **C144395** |
| J13b, J15 module ports | XH 6 | ✅ **C144397** |
| J13a Qwiic | SH 4 horizontal | ✅ C160404 |

**Sourced.** Both are the same JST XH family as the two already in use, so the
housings, crimps and crimp tool carry straight over:

| LCSC | Part | Pins | Rating | Price | Footprint |
| --- | --- | --- | --- | --- | --- |
| **C144395** | JST `B4B-XH-A(LF)(SN)` | 4 | 250 V / 3 A | ~$0.032 | `JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical` |
| **C144397** | JST `B6B-XH-A(LF)(SN)` | 6 | 250 V / 3 A | ~$0.048 | `JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical` |

Note the LCSC numbering runs with the family — C144394 is the 3-pin already in
use, C144395 the 4, C144397 the 6 — which is a small confirmation they are the
same listing series rather than lookalikes from another maker. Footprint names
follow KiCad's `Connector_JST` convention exactly as the 2- and 3-pin ones do;
confirm they are present in the library rather than assuming.

## The A11 divider can be one resistor value

**changed.** [values.md](values.md) specified 10 k / 11 k / 18 k, chosen before
this inventory existed. With 176 precision 10 k in stock, a version built
entirely from that one value is better on every axis that matters:

| | Three values | **One value** |
| --- | --- | --- |
| Network | 10 k / 11 k / 18 k | 10 k pull-up, 10 k on `/CHG`, **2×10 k series** on `/PGOOD` |
| Levels | 3.300 / 2.121 / 1.729 / 1.339 V | 3.300 / 2.200 / 1.650 / 1.320 V |
| Minimum gap | 390 mV | 330 mV |
| Worst case | 377 mV at 1% | **329 mV at 0.1%** |
| Unique parts | 3 | **1** |
| Resistor count | 3 | 4 |

### Why the smaller separation is the better choice

330 mV looks like a downgrade from 390 mV, and read on its own it is. But
separation is not a score to maximise — it is a threshold to clear, and past
that point more of it buys nothing.

**What the number has to achieve** is that the four voltage bands never overlap
once resistor tolerance, reference drift and ADC noise are accounted for, so the
firmware can never mistake one charge state for another. That is a pass/fail
question, not a scale.

**Both designs pass it by an enormous margin.** 330 mV is **409 ADC counts** of
gap between the closest two states. Noise on a filtered pin like this is a
handful of counts. The separation could shrink by a factor of ten and the
reading would still be unambiguous — which is exactly what the earlier
Monte-Carlo showed when the three-value network still held at 5% parts.

So the extra 60 mV is headroom that will never be touched. It is a bridge rated
for fifty tonnes instead of forty when the heaviest thing crossing weighs two.

**What it costs is real, though.** Three distinct values mean three BOM lines,
three reels to buy, and three feeder positions on the assembly line — where one
value means one of each. On a small run the per-unique-part handling is a
meaningful fraction of the assembly cost, and it recurs on every build.

**And the single value is the more accurate part.** The stocked 10 k is **0.1%**,
ten times tighter than the 1% the analysis assumed. So in practice the one-value
network degrades from 330 mV nominal to 329 mV worst case — essentially not at
all — while the three-value network at ordinary 1% parts drops from 390 mV to
377 mV.

The one-value network is therefore *less* accurate on paper and *more* accurate
in the drawer, and it is cheaper to build. That is the whole argument.

Use the stocked 0.1% part for all four.

## The RGB LED

**CHANZON 5 mm, common anode, 4-pin** — Amazon `B01C19ENFK`, 100 pcs.

**Common anode is the one that works.** Anode to the 5 V rail, the three cathodes
to D26/D27/D29 with the GPIOs sinking, three resistors and nothing else. The
common-*cathode* version of the same product (`B01C19ENDM`) would have needed a
high-side switch per channel — a PNP, a base resistor and a pull-up each, twelve
parts instead of three — because a 3V3 GPIO cannot drive a high side off 5 V.
Worth knowing the two listings differ by four characters.

**Get the diffused version.** The same part is available diffused from
AliExpress at the same specification, and that is the one to buy — the
water-clear listings are a trap for this application.

The status scheme in [indicators.md](indicators.md) is built on *mixed* colours:
amber is red plus green, magenta is red plus blue. An RGB LED is three separate
dice under one lens. Diffused blends them into a single colour; **water-clear
shows three coloured dots**, so amber reads as a red dot beside a green dot,
which nobody recognises as a state across a stage. Diffusion is doing real work
here, not cosmetics.

**Confirmed common anode.** Specification from the vendor:

| | Value |
| --- | --- |
| Forward voltage @ 20 mA | **R 2.0–2.2 V, G 3.0–3.2 V, B 3.0–3.2 V** |
| Viewing angle | 30° clear lens, **20° matte** |
| Package | 5 mm, 4 pin |

Those numbers confirm why 3V3 drive was never going to work: green and blue want
3.0–3.2 V against a GPIO that manages about 3.15 V.

### Series resistors

Common anode on the 5.0 V rail, cathodes through resistors to the GPIOs, which
sink. Allowing ~0.35 V of output-low drop:

| Channel | Vf | R | Resulting current |
| --- | --- | --- | --- |
| Red | 2.0–2.2 V | **510 Ω** | 4.80 – 5.20 mA |
| Green | 3.0–3.2 V | **300 Ω** | 4.83 – 5.50 mA |
| Blue | 3.0–3.2 V | **300 Ω** | 4.83 – 5.50 mA |

Note the red resistor is nearly double the other two for the *same* current —
that is the whole reason a common value fails.

**These are a starting point, not the answer.** Equal current does not give equal
perceived brightness: a green die is typically three to five times more luminous
per milliamp than red or blue, so at 5 mA each the mix will come out
green-dominant and amber will read as yellow-green. **Expect green's resistor to
rise substantially** — perhaps to 900 Ω–1 kΩ — before the mixes look right.

Tune by eye against the state table in [indicators.md](indicators.md), check
that amber and magenta are nameable rather than merely different, and **record
the values here** once they are settled.

At 5 mA per channel the worst case is 15 mA with all three lit, which is inside
both the per-pin and total sink limits and already inside the power budget.

**The 20° viewing angle is narrow** for a panel indicator. It wants to point at
the player rather than out of the front of the instrument, or to sit behind a
diffuser or light pipe that spreads it. Worth settling with the panel rather
than discovering on stage.

**Measure the forward voltages before choosing the series resistors.** ~390 Ω is
a placeholder based on typical figures; the real values come from this part at
the current you actually want. Red will differ from green and blue by around a
volt, so the three resistors will differ too — a common value is what broke the
original 3V3 scheme.

## Still to source

**Actives**

| Part | LCSC | Note |
| --- | --- | --- |
| BQ24074RGTR | **C54313** | QFN-16-EP 3×3, Economic assembly ✅ |
| TPS61023DRLR | **C919459** | SOT-563, Economic assembly ✅ |
| 1 µH inductor | **C354578** | CENKER CKCS4018-1uH/N — 4×4 mm shielded, 25 mΩ, 2 A RMS, **4.2 A Isat** |
| SS34 Schottky | **C8678** | MDD, SMA (DO-214AC), 40 V / 3 A, 550 mV @ 3 A. **JLC Basic** — no setup fee. |
| 74HC14 | **C5605** | Nexperia 74HC14D, SOIC-14. Hex Schmitt inverter — switch debounce. Stock KiCad symbol and footprint. |
| MCP6002 | **C116706** | Microchip MCP6002-I/SN, SOIC-8. Dual rail-to-rail, 1 MHz, 1.8 V min. **Audio-in gain stage, DNP.** ~$0.16 |

The inductor is the only one with real selection content, so here is the working.
Worst case is a 350 mA load at a 3.0 V cell: 0.65 A of DC current and 1.2 A p-p
of ripple at 1 µH. Derating inductance 30% as the datasheet instructs pushes
ripple to 1.71 A p-p and the **peak to 1.51 A**. 4.2 A of saturation is nearly
three times that, and 2 A RMS against 0.65 A DC is equally comfortable.

**Passives — jellybean, and all in JLC's Basic library**

| Value | Qty | Where | Note |
| --- | --- | --- | --- |
| 10 kΩ 0.1% 0603 | 4 | A11 encoder | **C374544, already in stock** |
| 887 Ω **1%** 0603 | 1 | `RISET` | 1% is a datasheet requirement, not a preference |
| 1.2 kΩ 0603 | 1 | `RILIM` | |
| 348 kΩ **1%** 0603 | 1 | boost FB upper | it sets the output voltage |
| 47.5 kΩ **1%** 0603 | 1 | boost FB lower | |
| 100 kΩ 0603 | 1 | boost `EN` pulldown | |
| 10 kΩ 0603 | ~3 | TS fallback, general | C15401, already used on absonus |
| 1 kΩ 0603 | ~4 | A10/A11 filters, charge LEDs | |
| 100 Ω 0603 | 7 | J11 series | |
| 510 Ω 0603 | 1 | RGB red | see above |
| 300 Ω 0603 | 2 | RGB green, blue | **expect green to rise on tuning** |
| 100 nF 0603 | 8 | **J5 wiper filters** | not 10 nF — see [values.md](values.md) |
| 10 nF 0603 | 2 | A10, A11 filters | |
| 100 nF 0603 | ~6 | decoupling | |
| 10 µF 0805 | ~3 | boost input, charger | X5R/X7R, ≥10 V |
| 100 µF | 1 | boost output bulk | ≥10 V; C3337 is the absonus electrolytic |
| Ferrite bead | 1 | boost output → Seed VIN | rated **≥1 A** |

Two of those are deliberate picks rather than defaults. **The ferrite bead
carries the whole instrument's current** — a signal-grade bead saturates and its
impedance collapses exactly when it is needed. And the **100 µF output bulk sits
at the boost output**, so its ESR shows up in the ripple; a ceramic in parallel
with the electrolytic is the usual answer if measured ripple comes out high.

**Mechanical**

| Part | Note |
| --- | --- |
| 10 kΩ NTC `103AT-2` | **or** a fixed 10 kΩ if the pack has no thermistor — TS cannot float |
| Barrel jack 5.5 × 2.1 | decided with the enclosure |
| Illuminated latching switch | in hand; **bezel diameter still to be measured** |
| JST-XH housings and crimps, 2 / 3 / 4 / 6 way | one crimp tool covers all four |

## Every connector is fitted on every board

JLCPCB fits the through-hole parts, which collides with "stuff per instrument" —
a machine-populated board cannot be stuffed differently afterwards. The choice
was between per-instrument BOM/CPL variants and fitting everything every time.

**Fit everything.** All fifteen connectors come to about **$0.65 per board**, of
which roughly half is unused on any given build. That is far less than the cost
of maintaining three order configurations, where one wrong line wastes a batch.

So the platform promise shifts one step outward, and gets stronger for it:

> One PCB, one BOM, one CPL. **Cable** per instrument, not stuff per instrument.

**The distinction that matters:** *connectors* are always fitted; *circuit
options* stay DNP. A connector nobody plugs into costs four cents and some board
area. A populated option that should not be there — an I2C pull-up on a UART, a
gain stage on a line-level input, the wrong sensor pulldown — is a fault.

| Always fitted | Stays DNP |
| --- | --- |
| J1–J16, all connectors and headers | I2C pull-ups (4.7 k) |
| Seed sockets | Audio gain stage and its network |
| | Sensor pulldowns on A4 / A5 |
| | Mic bias, carbon / electret / dynamic paths |
| | Audio-in coupling where a build has no input |

## Before ordering

- Both ICs are near-certainly **Extended**, so budget a per-unique-part setup
  fee of about $3 each. JLC prices it when the BOM goes up.
- **Reusing absonus footprints means reusing absonus mistakes too.** They are
  proven to fabricate, which is not the same as proven correct for this board —
  check the IDC pin-1 orientation and the JST polarity against this schematic
  rather than assuming they carry over.