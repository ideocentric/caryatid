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
| C158012 | JST-XH 2-pin vertical | `JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical` | on absonus | J6, J7, J8, J10 |
| C144394 | JST-XH 3-pin vertical | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | on absonus | J9 |
| C160404 | JST-SH 4-pin horizontal | `JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` | on absonus | **J13a, Qwiic** |
| C5289485 | LS18-P | `DIP787W45P254L927H533Q8` | on absonus | debounce, socketed |
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
| J3 latch, J4 charge LEDs, J12 RGB | **XH 4** | ❌ source |
| J13b, J15 module ports | **XH 6** | ❌ source |
| J13a Qwiic | SH 4 horizontal | ✅ C160404 |

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

330 mV is 409 ADC counts, and the earlier tolerance work showed the scheme
survives down to ~310 mV at 5% parts. Trading 60 mV of margin for **two fewer
SMT feeders and a part already on the shelf** is worth it, and at 0.1% the
worst case is 329 mV — effectively the nominal.

Use the stocked 0.1% part for all four. Precision is free here; it is what is in
the drawer.

## Still to source

Nothing exotic, but none of it is in the library yet.

**Actives**

| Part | LCSC | Note |
| --- | --- | --- |
| BQ24074RGTR | C54313 | QFN-16-EP 3×3, Economic assembly ✅ |
| TPS61023DRLR | C919459 | SOT-563, Economic assembly ✅ |
| SS34 Schottky | — | barrel-jack input protection |
| RGB LED, **common anode** | — | see [values.md](values.md); Vf sets the series resistors |

**Passives and mechanical**

- 1 µH inductor, saturation rated per [values.md](values.md)
- 100 µF output bulk, ferrite bead
- Resistors: 887 Ω 1% (`RISET`, 1% is a datasheet requirement), 1.2 kΩ
  (`RILIM`), 348 k / 47.5 k (boost divider), 1 kΩ, 390 Ω × 3 (RGB), 100 kΩ
  (`EN` pulldown)
- 100 nF × 8 for the J5 wiper filters — **not** 10 nF
- 10 kΩ NTC 103AT-2, **or** a fixed 10 kΩ if the pack has no thermistor
- Barrel jack 5.5 × 2.1
- JST-XH 4-pin and 6-pin, per the table above
- Illuminated latching switch — bezel diameter still to be measured

## Before ordering

- Both ICs are near-certainly **Extended**, so budget a per-unique-part setup
  fee of about $3 each. JLC prices it when the BOM goes up.
- **Reusing absonus footprints means reusing absonus mistakes too.** They are
  proven to fabricate, which is not the same as proven correct for this board —
  check the IDC pin-1 orientation and the JST polarity against this schematic
  rather than assuming they carry over.