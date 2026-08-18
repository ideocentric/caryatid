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
| **C41361038** | DS1023-1x20S21, 1×20 socket | `插件,P=2.54mm` | **36** | Seed sockets — Global Sourcing |
| C2897383 | 1×20 female socket | — | on absonus | **Seed sockets, the part actually used** |
| C158012 | JST **B2B-XH-A(LF)(SN)**, 2-pin | `JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical` | on absonus | J6, J7, J8, J10 |
| C144394 | JST **B3B-XH-A(LF)(SN)**, 3-pin | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | on absonus | J9 |
| C160404 | JST-SH 4-pin horizontal | `JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` | on absonus | **J13a, Qwiic** |
| ~~C5289485~~ | ~~LS18-P~~ | — | on absonus | **superseded** by the 74HC14, [ADR 0007](decisions/0007-rc-and-schmitt-instead-of-the-ls18-p.md) |
| — | *Daisy Seed footprint* | `Electrosmith_Daisy_Seed` | — | outline only; the module is not a BOM line |
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
| J6/J7/J8 switches, J10 FSR | XH 2 | ✅ C158012 |
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

## The charge LED — J4

J4 takes a **red/green common-anode bicolour** with no board change: three
terminals onto pins 1–3, pin 4 unused. The state table and the reasoning are in
[indicators.md](indicators.md).

**Candidate:** Amazon `B01CFZMO3I`, listed as diffused —
<https://www.amazon.com/Diffused-Lighting-Electronics-Components-Emitting/dp/B01CFZMO3I>

> **Its specification is UNVERIFIED.** The listing could not be read
> automatically, so nothing here is quoted from the vendor — not the forward
> voltages, not the package, not the pinout. Everything below is a requirement
> the part must be *shown* to meet, not a claim about this one.

**The green die is the whole question**, because J4 hangs on `VOUT` — the cell,
about **4.2 V falling to 3.0 V**, not a regulated rail.

| Green chemistry | Vf | Verdict |
| --- | --- | --- |
| AlGaInP, yellowish-green | ~2.1 V | works across the whole range |
| InGaN, true green | 3.0–3.2 V | **dims, then dies as the cell drains** |

That is the identical failure that stopped the RGB being driven from 3V3, one
rail further down. The RGB part was confirmed at 3.0–3.2 V green; **if this
bicolour uses the same die it is the wrong part for J4**, however good it looks
on the bench at full charge.

Before committing:

1. **Measure Vf on the green die**, or find it stated. Under ~2.4 V is safe;
   3.0 V and above is disqualifying.
2. **Confirm common anode**, not common cathode. The two RGB listings differ by
   four characters for exactly this, and the wrong one needs a high-side switch.
3. **Confirm diffused.** Amber here is red and green mixed in one lens; a
   water-clear part shows two coloured dots, which nobody reads as a state —
   the same argument that governs the RGB.
4. **Test it at 3.0 V, not 4.2 V.** A green that looks fine on a full cell is
   precisely the failure mode: it goes dark when the battery is low, which is
   when you most want to see the charger working.

Then trim R9 and R10 by eye — red usually swamps green at equal current, so
amber tends to read orange-red.

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

## The cell

**Protected 18650, 3000 mAh design basis** — the specified cell is 3400 mAh, so
every derived figure below is conservative. ~18 × 65 mm bare, **~18 × 69 mm
protected** — the protection PCB adds length at the negative end, which is the
dimension that catches people fitting a holder.

| | |
| --- | --- |
| Charge current | 1 A = **0.33C** — gentle for any 18650 |
| Charge time | ~3.5 h |
| Runtime | 10.8 h quiet, **6.5 h typical**, 4.6 h loud |
| Connector | none — the cell seats in BT1, which cannot be wired backwards |

**Protection is a requirement, not a preference** (P-7: over-charge,
over-discharge, over-current). A protected cell carries a small PCM under the
wrap at the negative end — a MOSFET pair that disconnects the cell on
over-discharge (~2.5–2.8 V), over-charge (~4.25–4.3 V) and over-current. A bare
cell needs a separate protection board.

**On this board the PCM is the only over-discharge protection there is.** The
bq24074 protects the cell while *charging* — it terminates properly and limits
current — but nothing here protects it while *discharging*. There is no
low-voltage cutoff; the boost keeps pulling until it browns out. Taking a
lithium-ion cell below ~2.5 V dissolves copper from the anode collector, which
can plate back as an internal short on the next charge. So P-7 is satisfied by
the cell, not by the board, and a bare cell in this holder is a genuine hazard
rather than a specification quibble.

That is also why the A10 gauge exists: when the PCM trips the instrument stops
dead with no warning, so "battery critical" must fire well above ~2.8 V.

**The PCM is not a thermistor.** The cell has **no** thermistor either way, so
the charger's `TS` pin gets a fixed 10 kΩ — it cannot float. Two different
protections, easily conflated.

### Which cell to buy

**Protected, button-top, ~69 mm.** Protected cells are essentially always
button-top; a flat-top bare cell may not seat or make contact.

**The cell is
[Orbtronic 3400 mAh protected](https://www.orbtronic.com/protected-3400mah-18650-li-ion-battery-panasonic-ncr18650B-orbtronic)**
— Panasonic NCR18650B inside, button top, **68.9 mm**, inside what the
BH-18650-PC is cut for.

| | Spec | |
| --- | --- | --- |
| Capacity | 3400 mAh, 12.2 Wh | design basis is 3000, so runtimes above are a **floor** |
| Length | **68.9 mm ±0.03** | the number the holder choice turned on |
| Diameter | 18.6 mm ±0.03 | wider than a bare cell's ~18.4; the holder is cut for protected |
| Weight | 46 g | |
| Nominal | 3.6–3.7 V, charge to 4.2 V | matches what the bq24074 delivers |
| Max continuous | **2C = 6.8 A** | board's worst case is ~1.5 A — 4.5× margin |
| Pulse, 2–4 s | 10 A | |
| Core cell | Panasonic NCR18650B, UL MH12210 | |
| Protection ICs | Seiko-Ablic, Japan, welded external PCB | |

**Every protection threshold clears the board by a wide margin**, which is the
result you want — the PCM is a backstop that should never fire in normal use:

| PCM trips at | Board does | Margin |
| --- | --- | --- |
| Over-charge **4.33 V** | bq24074 terminates at **4.2 V** | 130 mV |
| Over-discharge **2.5 V** | runtime figures stop at **3.0 V** | 500 mV |
| Over-current **10–12 A** | ~1.5 A peak at low charge | ~7× |

Also over-temperature and dual (internal + external) short-circuit protection.

**The over-temp protection is inside the cell's PCM and is not a thermistor
output.** `TS` still gets a fixed 10 kΩ — the charger has no way to see it. Easy
to misread as changing that.

**Charge rate** is 1 A = 0.29C on 3400 mAh, gentler than the 0.33C the values
were derived at. The vendor warns never to charge above 4.25 V; the bq24074 is a
4.2 V CC/CV part, so it is exactly the charger they ask for.

**Buy two.** Cells are priced and sold individually. The socketed holder was
chosen over a soldered pack precisely so a spare lives in the bag instead of the
instrument dying — and buying a pair includes a plastic carry case, which is not
a nicety. **A loose 18650 in a gig bag is a short-circuit hazard**: the positive
button and the can are both exposed, and a key or a jack plug across them will
dump 6.8 A into a dead short. Carry the spare in the case.

Equivalents if Orbtronic is out of stock — all protected, button-top, ~69 mm:

- [Liion Wholesale, same NCR18650B cell](https://liionwholesale.com/products/protected-panasonic-sanyo-ncr18650b-3400mah-5a-li-ion-18650-button-top-battery-wholesale-discount) — 5 A rated
- [Nitecore NL1834](https://18650battery.com/products/nitecore-nl1834-18650-3400mah-battery-protected-button-top) — 6 A

**Ignore anything claiming more than ~3600 mAh.** A genuine 18650 tops out around
3500; higher numbers are fake wraps around smaller cells.

**The holder is on the board**, soldered, rather than a pack tacked into the
enclosure. That removes the last hand-crimped power loom and with it the
reverse-polarity risk that had no protection behind it — a soldered holder cannot
be wired backwards. The cell stays replaceable, which for a gigging instrument
means a spare in the bag instead of a dead instrument.

**There is no remote-pack option.** J2 was removed at layout: nothing on the
platform wanted it, and it was the last route by which a reversed cell could
reach an unprotected charger input.

### The holder — settled

**BT1 = MPD `BH-18650-PC`, `C5339083`**, footprint
`Battery:BatteryHolder_MPD_BH-18650-PC` (stock KiCad, pads verified against the
drawing: 72.90 mm terminals, 55.61 mm mounting holes).

**It is rated for protected cells**, stated on the drawing rather than inferred:
*"This battery holder is designed for use with protected 18650 batteries
(PCB)."* That was the open question — protected cells run ~69 mm where most
holders are cut for 65 mm unprotected, because the protection board adds length
at the negative end.

| | |
| --- | --- |
| Body | 77.7 × 20.9 mm, **21.31 mm tall** |
| Material | self-extinguishing thermoplastic polyester, UL94V-0, −40…+180 °C |
| Assembly | **Economic and Standard** — same tier as the charger and boost |
| Mounting | Ø3.2 mm holes; the drawing says 2-56 screws, eyelets or adhesive |

**Bolt it down as well as soldering it.** The two solder tabs are not a
mechanical mount for a 46 g cell in something that gets carried to gigs.

**Second source, pin-identical:** MPD `BK-18650-PC2` — same 72.90/55.61 layout,
also rated for protected cells, and it carries vibration and 150 G shock test
results the BH does not ("no dislodgement of the cell"). Polypropylene rather
than polyester, so a narrower temperature range. Either drops into the same
footprint.

**Rejected:** Keystone 1042. Its courtyard is 87.9 mm against the MPD's 79.2 mm
— on a 90 mm edge that leaves about a millimetre a side — and its protected-cell
fit is unverified.

**Firmware should warn before the PCM acts.** A protected cell cuts off around
2.5–2.8 V, at which point the instrument simply stops. The A10 gauge exists so
"battery critical" fires well above that — the amber and red states in
[indicators.md](indicators.md) are what turns a dead stop into a warning.

**Alternative if an enclosure is ever thin:** a flat LiPo pouch — a 605080 is
6 × 50 × 80 mm for about 3000 mAh against the 18650's 18 mm diameter. Not
replaceable, and it needs mechanical protection from puncture, so it is the
choice only when thickness actually binds. It does not here: a telephone is
chunky, and absonus already lives with 18 mm.

### The BUD CU-477, measured from its STEP model

BUD supplied `CU-477.STEP`. It lives at `local/reference/CU-477.STEP` in the
**loa** repo, which is gitignored — so the numbers below are the record, not the
file.

| | mm | inch |
| --- | --- | --- |
| Outer envelope | 119.5 × 187.7 × 38.1 | 4.70 × 7.39 × 1.50 |
| Bottom panel, outer | 118.3 × 186.5 | 4.66 × 7.34 |
| Interior clear, 6–25 mm above the floor | ~110 × 170 | approximate |

The interior figure is read off a sparse point cloud and should be treated as
indicative. The working rectangle stays **95.2 × 165.1 mm** (3.75″ × 6.5″), which
is the deliberately conservative number allowing for the sloped sides.

**The 150 × 90 board clears all three.** Against the conservative rectangle it
has +5.2 mm on the short axis and +15.1 mm on the long; against the STEP
interior, +20 mm on both. The enclosure is not a constraint on this outline.

**The floor is blank.** The model carries 108 M3-sized holes, and every one of
them is in a wall or a flange, at six distinct heights — none in the bottom. So
the case has to be drilled for the board standoffs, and there is no existing
pattern to reuse or to avoid.

**Drill pattern for the standoffs.** caryatid's four M3 holes sit at board
(5, 5), (145, 5), (5, 85), (145, 85), which is a **140 × 80 mm rectangle**
centre-to-centre. The board's 150 mm axis runs along the enclosure's long axis.
Centred on the floor, in the STEP file's own coordinate frame:

| Hole | X | Z |
| --- | --- | --- |
| ×4 | **±40 mm** | **±70 mm** |

That leaves ~19 mm of floor beyond the holes on the short axis and ~23 mm on the
long one, so the pattern still clears the walls.

**Mechanical — all panel-mount, all reaching the board by wire**

| Part | Spec | Panel hole |
| --- | --- | --- |
| DC jack | **DC-099**, 5.5 × 2.1, 30 V / 10 A, threaded | ~8 mm — confirm |
| Audio jacks | 3.5 mm stereo, panel mount | ~6 mm — confirm |
| LED bezel | 5 mm LED, black plastic, snap-in, **12.5 mm long** | **8 mm** |
| Illuminated latching switch | 3–9 V lamp, latching | **Ø12 / 16 / 19 — the one still unknown** |
| Board standoffs | M3 kit | — |
| 10 kΩ NTC `103AT-2` | **or** a fixed 10 kΩ if the pack has no thermistor — TS cannot float | — |
| JST-XH housings and crimps, 2 / 3 / 4 / 6 way | one crimp tool covers all four | — |

**The switch bezel diameter is the only outstanding mechanical number.** Its
electrical side has been settled since the lamp turned out to be a 3–9 V variant
with internal limiting, so `R_LED` is a 0 Ω link; measuring the lamp current at
5 V against 6 V is a brightness sanity-check, not a gate on anything.

**Board clearance**, for sizing standoffs and the shell cavity:

| | Height |
| --- | --- |
| 1×20 socket | 8.5 mm |
| Seed sitting on it | +2 mm — **10.5 mm, the tallest stack** |
| 2×5 IDC box header | ~9 mm |
| 220 µF electrolytic | 5.4 mm |

**The IDC headers do not set panel standoff.** They are internal — ribbon runs
from them out to the panel controls — so they need clearance under the panel and
nothing more. Standoff length is set by the enclosure, and for loa that means the
phone shell.

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
## Checked against the JLCPCB inventory and the absonus order

`local/reference/` holds `Parts Inventory on JLCPCB.xlsx` and `bom.xls`, the
absonus BOM **as actually ordered**. Both are gitignored, so what they establish
is recorded here.

**Already in stock**, quantities from the inventory:

| part | | qty |
| --- | --- | --- |
| `C374544` | AR03BTDX1002A010, 10 kΩ 0.1% 0603 | **176** |
| `C4749194` | DS254P-2X5-L0, IDC 2×5 | **176** |

Both are already mapped, so 5 of caryatid's placed parts need no purchase.

**Two things the ordered BOM settled that the prose could not:**

- **`C3337` is a 220 µF part in `CP_Elec_5x5.4`** — it was ordered as such. That
  makes this document right and [power-sheet.md](power-sheet.md) wrong to have
  mapped C7 to it; power-sheet.md is corrected. C7 is 100 µF in
  `CP_Elec_6.3x5.4` and remains unsourced.
- **`C2897383` is the Seed socket**, ordered and fabricated. Decision G is
  closed in its favour over `C41361038`, which the inventory shows at quantity
  zero under Global Sourcing.

`C4211` (3 kΩ 0603) is also in the absonus order and matches R45 here — but R45
is **DNP**, so it is not needed for assembly.

## The 56 parts still without a part number — five decisions, not fifty-six

`tools/fab_package.py` exits nonzero while any placed part lacks an LCSC code.
34 of 92 are covered from what this document and [power-sheet.md](power-sheet.md)
already state. The remaining 58 collapse into **seven decisions**, because a
family choice settles every value inside it.

### A — one 0603 resistor family: 11 values, 33 parts

| value | qty | | value | qty |
| --- | --- | --- | --- | --- |
| 1 kΩ | 14 | | 46k4 | 1 |
| 100 Ω | 7 | | 0 Ω | 1 |
| 100 kΩ | 3 | | 348 kΩ **1%** | 1 |
| 300 Ω | 2 | | 47k5 **1%** | 1 |
| 1k2 | 1 | | 510 Ω | 1 |
| 887 Ω **1%** | 1 | | | |

Pick one Basic 1% 0603 series and every value follows. **Three constraints are
already fixed and must not be relaxed:**

- **R3 887 Ω must be 1%** — a datasheet requirement, not a preference. The
  bq24074 short-tests `RISET` at maximum charge setting.
- **R7 348 kΩ and R8 47k5 set the boost output voltage.** Tolerance here is
  output accuracy, and [values.md](values.md) leaves only 109 mV to the OVP
  minimum.
- **R4 46k4 and the three above are E96 values**, which are frequently
  *Extended* rather than Basic at JLC. That is the one thing to check before
  assuming a single family covers the set — it is where a per-part setup fee
  would appear.

### B — one 0603 MLCC choice: 4 values, 14 parts

100 nF ×9, 10 nF ×2, 220 nF ×2, 1 µF ×1. All sit on rails at 5 V or below, so
16 V X7R is ample and cheap. One dielectric-and-voltage decision covers all four.

### C — one 0805 MLCC choice: 3 values, 6 parts

10 µF ×4, 10 µF ×1 **at 25 V**, 22 µF ×1. **C1's 25 V rating is not
negotiable** — it sits on the raw barrel input, which reaches 9 V, and
[power-sheet.md](power-sheet.md) states it. The other five are on the cell and
5 V rails.

### D — C7, 100 µF electrolytic

~~Blocked on a documented conflict.~~ **Conflict resolved, part still needed.**
The absonus order shows `C3337` really is 220 µF in `CP_Elec_5x5.4`, so
power-sheet.md was wrong to map C7 to it and has been corrected. C7 is 100 µF in
`CP_Elec_6.3x5.4`, ≥ 10 V, and has no candidate yet.

### E — FB1 ferrite bead, 0805

Rated **≥ 1 A** per power-sheet.md, which is the only constraint written down.
The impedance-at-frequency is not specified anywhere and needs choosing — it is
sitting between the boost output and everything downstream, so it is picked
against the boost's 1 MHz switching, not arbitrarily.

### F — J16, 2×4 pin header 2.54 mm

One commodity part. No constraint beyond the footprint.

### G — A1/A2, the Seed sockets: ~~choose between two~~ **settled**

**`C2897383`.** It is what the absonus BOM actually ordered, so it is proven in
a fabricated board. `C41361038` sits at quantity zero under Global Sourcing in
the inventory. Two per caryatid, one per 1×20 strip.
