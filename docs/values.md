# Component values

Derived from the TI datasheets — bq24074 `SLUS810N`, TPS61023 `SLVSF14B` — not
from application notes or reference designs. Constants are quoted from the
electrical characteristics tables so the arithmetic can be checked.

Document numbers, revisions and links for every part are in
[datasheets.md](datasheets.md); the PDFs live in `local/datasheets/`, which is
gitignored because they are the manufacturers' copyright.

Three of these changed a number in the platform spec. They are marked **changed**.

## Charger — bq24074

`ICHG = KISET / RISET`, with **KISET = 890 AΩ typical (797 min, 975 max)**.

| Charge current | RISET | E96 1% |
| --- | --- | --- |
| 0.5 A | 1780 Ω | 1780 |
| **1.0 A** | **890 Ω** | **887** |
| 1.5 A | 593 Ω | 590 |

The spec's 890 Ω for 1 A is correct. **But the tolerance is not in the
resistor** — KISET alone spans 797–975, so 887 Ω delivers **0.90 A to 1.10 A**
across the part distribution. Budget for ±10% and do not size a supply or a
charge-time claim on the nominal.

The datasheet is explicit that **RISET must be 1%**, and not for accuracy: the
part runs a short test on RISET at the maximum charge setting, and a loose
resistor can trip it.

**Charge time**, 3400 mAh cell at 1 A, allowing for the constant-voltage tail:
about **4.0 hours**. Requirement P-9 asks for "fast enough between soundcheck
and downbeat", which this is not. 1.5 A would give ~2.7 h. The trade is heat and
cell life; 1 A on this cell is 0.29C and gentle, 1.5 A is 0.44C and still within
spec. **Left at 1 A**: the barrel jack means charging can start early, and cell
longevity is worth more than an hour.

> **These figures were re-derived from the cell actually bought, 2026-08-23.**
> They previously assumed a 3000 mAh design basis and read ~3.5 h at 0.33C. The
> ordered cell is the Orbtronic 3400 mAh, so charge takes about 13% longer and
> the C rate eases. Runtime moved the other way; see below. The derivation is
> CC to roughly 80% then the constant-voltage tail, which is what reproduces the
> original numbers at 3000 mAh.

`IIN-MAX = KILIM / RILIM`, **KILIM = 1550 AΩ**, and **RILIM must be 1.1 kΩ to
8 kΩ**.

That range is a real constraint: it caps the input limit at **1.41 A**, not the
1.5 A the headline figure suggests. The input limit must exceed charge current
plus system load, or the charger throttles charging to feed the system.

| RILIM | Input limit |
| --- | --- |
| **1.2 kΩ** | **1.29 A** |
| 1.5 kΩ | 1.03 A |
| 2.0 kΩ | 0.78 A |

**1.2 kΩ**, giving 1.29 A: 1.0 A charge plus ~290 mA of system, which matches
the budget below.

**TS** — 10 kΩ NTC, `103AT-2` type, in the battery pack. **If the pack has no
thermistor, fit a fixed 10 kΩ from TS to VSS**; the pin is not optional and
floating it will not work.

**`/CHG` and `/PGOOD` are open-drain**, pulling to VSS. Confirmed from the pin
table — which is what makes both the hardware charge LEDs and the A11 encoding
possible.

## Boost — TPS61023

**changed: output is 5.0 V, not 5.2 V.**

`VOUT = VREF × (1 + R1/R2)`, **VREF = 595 mV typical (580–610)** in PWM mode.

The reason for the change is `VOVP`, the output over-voltage protection, whose
**minimum trip is 5.5 V**. Worst case stacks the reference tolerance on the
divider tolerance:

| Target | R1 / R2 | Nominal | 1% worst case | Margin to OVP min |
| --- | --- | --- | --- | --- |
| 5.2 V | 365k / 47.5k | 5.167 V | 4.948 – **5.391 V** | **109 mV** |
| **5.0 V** | **348k / 47.5k** | **4.954 V** | 4.744 – 5.168 V | **332 mV** |

109 mV between a worst-case part and its own protection threshold is not a
margin. The 5.2 V figure came from Adafruit's PowerBoost, where the extra
200 mV pays for drop down a USB cable — there is no cable here, the boost feeds
a Seed VIN pin two centimetres away. **Nothing downstream needs 5.2 V**, and the
switch lamp cannot tell the difference.

R2 = 47.5 kΩ keeps divider current at ~12.5 µA — comfortably over the 100× the
datasheet asks for against FB leakage (4–20 nA), and under the 300 kΩ ceiling it
sets for R2.

**Inductor** — the part works with **0.37 µH to 2.9 µH**; 1 µH is the datasheet's
own reference. Size the saturation rating from `IL(DC) = VOUT × IOUT / (VIN × η)`
at **minimum** input, maximum load, and derate the inductance 30%.

**Switching is 1 MHz** above 1.5 V input. Relevant to layout: keep the
`VIN`/`L`/`SW`/`COUT` loop small, and note that 1 MHz is far enough above the
analogue bus corner (below) to be well attenuated.

## Power budget

`I_in = VOUT × I_out / (VIN × η)`, η = 0.90.

| Load | from 4.2 V | from 3.6 V | from 3.0 V |
| --- | --- | --- | --- |
| 150 mA | 0.20 A | 0.23 A | 0.28 A |
| 250 mA | 0.33 A | 0.39 A | 0.46 A |
| 350 mA | 0.46 A | 0.54 A | 0.65 A |
| 600 mA *(with a radio)* | 0.79 A | 0.93 A | **1.11 A** |

### Where the 5 V load actually goes

The scenario totals above are estimates, not a tally. This is the tally — every
pad on `+5V`, so the scenarios can be checked rather than trusted. **Ten pads
are on the rail; two of them are not loads**: C7 is the 100 µF bulk cap, and
FB1 pin 2 is the source, the ferrite's output side.

| Load | Ref | Basis | Current |
| --- | --- | --- | --- |
| **Daisy Seed** | A2-39 | **derived, see below** | **~100 mA MCU alone** |
| RGB status | J12-1 | R40 510 Ω red, R41/R42 300 Ω green/blue, common anode | 5.9 / 6.7 / 6.3 mA per die |
| — worst assigned state | | amber (red+green) | **12.6 mA** |
| — all three | | white, deliberately unassigned | 18.9 mA |
| **Mic bias L** | R52 | 220 Ω, **only when JP1 is on `2-3` (carbon)** | **11–21 mA** |
| **Mic bias R** | R54 | 220 Ω, **only when JP4 is on `2-3` (carbon)** | **11–21 mA** |
| **Switch lamp** | R5 | 0 Ω link; lamp limits internally, **unmeasured** | **unknown** |
| Mic bias, electret L | R51 | 2k2 from 3V3A, JP1 on `1-2` | 1.5 mA |
| Mic bias, electret R | R53 | 2k2 from 3V3A, JP4 on `1-2` | 1.5 mA |
| Comms A module | J19-1 | external, no allowance stated | unknown |
| Comms B module | J15-1 | external, no allowance stated | unknown |
| Expansion | J16-1 | external, no allowance stated | unknown |
| Bulk decoupling | C7-1 | 100 µF, no DC path | 0 |

**The Seed's own datasheet publishes no current figure.** The ~100 mA is derived,
not quoted: `DS12556` Rev 8 Table 20 gives the STM32H750 at **135 mA typical**
in Run mode, VOS1, 400 MHz, all peripherals enabled, T<sub>J</sub> = 25 °C; that
is 3.3 V current, and it reaches the 5 V rail through the Seed's own TPS62170
buck, so 135 × 3.3 / (5 × 0.9) ≈ **99 mA**. **It excludes the module's SDRAM,
codec, QSPI flash and analogue LDO**, none of which are separately sourced, and
the same table reaches 730 mA at 125 °C. Treat 100 mA as a floor for the MCU
core, not as the module's consumption.

Three entries are genuinely open, and they are the reason the tally cannot yet
be reconciled against the 250 mA "typical" row:

- **The mic bias pair is the largest unresolved item — up to 41 mA together**,
  which is 16% of the typical scenario. 220 Ω is a low bias value, and
  [audio.md](audio.md) still lists *measure the handset capsule* as open: the
  capsule type sets where it sits and therefore the current.
- **The switch lamp is unmeasured.** [capture-checklist.md](capture-checklist.md)
  already asks for a meter in series at both voltages; that reading lands here.
- **The three connector 5 V pins have no stated allowance.** The 600 mA "with a
  radio" row implicitly reserves headroom for them, but nothing attributes it.

None of this threatens the copper — the `+5V_RAW` pour necks to 0.80 mm, good
for 2.03 A at a 10 °C rise, which is 3.4× the worst documented case. **These
numbers matter for runtime**, which is what the table below quotes.

Runtime on the **3400 mAh** cell, ~2833 mAh usable down to 3.0 V:

| | Load | From cell | Runtime |
| --- | --- | --- | --- |
| Quiet | 150 mA | 231 mA | **12.3 h** |
| Typical | 250 mA | 386 mA | **7.3 h** |
| Loud, LEDs lit | 350 mA | 540 mA | **5.2 h** |

Re-derived 2026-08-23 from the cell actually bought. The earlier table assumed
3000 mAh with 2500 usable; the usable fraction is unchanged at 83.3%, so 3400
gives 2833.

A gig is covered comfortably. Note the last row of the first table: a WiFi
module pushes cell current past 1 A at low state of charge, which is the
quantified version of the earlier advice to keep radios on mains builds.

## Indicators

**changed: the RGB cannot be driven from a 3V3 GPIO.**

The spec's "3 × series R (~330 Ω) from D8–D10" works for red and fails for the
other two. An STM32 output-high is roughly 3.15 V under a few milliamps, and
green and blue capsules have forward voltages around 3.0–3.1 V:

| Channel | Vf | Headroom | Through 330 Ω |
| --- | --- | --- | --- |
| red | ~2.0 V | +1.15 V | 3.5 mA |
| green | ~3.0 V | +0.15 V | **0.45 mA** |
| blue | ~3.1 V | +0.05 V | **0.15 mA** |

Green and blue will be invisible, and no resistor value fixes it — there is no
voltage to work with. **Drive from the 5 V rail instead, common anode, GPIOs
sinking.** Three resistors and nothing else: with 5 V against Vf 3.1 V there is
1.9 V to drop, so ~390 Ω gives 5 mA. A GPIO driven high leaves the LED seeing
5 − 3.3 = 1.7 V, which is below Vf, so it stays dark.

### The 5 V tolerance question, verified

All three pins are `FT` — 5 V tolerant — per Table 7 of `DS12556`:

| Seed | MCU | I/O structure |
| --- | --- | --- |
| D26 | PD11 | `FT_h` |
| D27 | PG9 | `FT_h` |
| D29 | PB14 | `FT_u` |

`FT_u` on D29 looks alarming and is not. The `_u` marks a USB alternate
function; footnote 6 — *"when the pin is used in USB configuration
(OTG_HS_ID/OTG_HS_VBUS), the I/O is supplied by VDD33USB, otherwise it is
supplied by VDD"* — is attached to **PB12 and PB13 only**, which carry the
`(6)` marker. PB14 does not. As a GPIO it runs from VDD like any other FT pin.

**The absolute maximum is conditional, though, and worth knowing:**

```
VIN(FT_xxx) max = Min( Min(VDD, VDDA, VDD33USB, VBAT) + 4.0 , 6.0 ) V
```

With all rails at 3.3 V that is **6.0 V** and 5 V drive has a volt of margin.
If `VDD33USB` were unpowered the term collapses to **4.0 V**. The Seed's own USB
works — DFU and USB MIDI — and its `OTG_FS` pins PA11/PA12 are themselves
`FT_u`, so VDD33USB must be supplied. Confirm on the Seed schematic if you want
it airtight.

**In this circuit the pin never sees 5 V anyway.** With the LED between the 5 V
rail and the pin, a floating pin only rises to `5 V − Vf`. The worst case is the
**red** channel, whose low Vf at leakage currents puts the pin around 3.5 V —
inside even the degraded 4.0 V limit. Green and blue float lower still. So the
scheme is safe under either answer, and the red channel is the one to measure if
you want certainty.

The part is settled: **5 mm, diffused, common anode**, Vf of **2.0–2.2 V red**
and **3.0–3.2 V green and blue** at 20 mA. Those figures confirm the diagnosis
above — green and blue want more than a 3V3 GPIO can deliver.

Series resistors are **510 Ω red, 300 Ω green and blue** for ~5 mA each from the
5 V rail. The red one is nearly double for the same current, which is exactly why
a single common value fails. Expect green's to rise on tuning, since equal
current is not equal brightness. Full working in [sourcing.md](sourcing.md).

**Switch lamp** — 3–9 V rated, current limiting internal, so `R_LED` is a 0 Ω
link on a 0603 footprint. See [indicators.md](indicators.md).

## Analogue front ends

**changed: J5 wiper filtering.** The spec's 220 Ω / 10 nF is looser than it
looks, because a pot contributes its own source impedance:

| Network | Pot at either end | Pot mid-travel |
| --- | --- | --- |
| 220 Ω / 10 nF | 72 kHz | **5.9 kHz** |
| **1 kΩ / 100 nF** | 1.6 kHz | **455 Hz** |

At a 1 kHz control rate anything above ~500 Hz folds back into the samples. The
220 Ω / 10 nF version attenuates the 1 MHz switcher fine but does nothing about
the 5–20 kHz band that actually aliases. **1 kΩ / 100 nF** — which is what loa's
own hardware doc specified before the platform existed — costs the same and
lands the corner where it belongs. 350 µs of settling is imperceptible on a
knob.

**A10 battery gauge** — 100 k / 100 k from BAT, 1 kΩ / 10 nF into the pin.
Draws **~21 µA continuously, including while switched off**: about 0.5 mAh a
day, 92 mAh over six months. Acceptable against 3400 mAh, but it is the one
thing on the board that never stops.

**A11 charge status** — **superseded by the one-value version**: 10 k pull-up,
10 k on `/CHG`, 2×10 k in series on `/PGOOD`, all from the 0.1% part already in
stock. 330 mV minimum separation instead of 390 mV, in exchange for two fewer
SMT feeders. See [sourcing.md](sourcing.md). Derivation of the original three-
value network is in [indicators.md](indicators.md) and still explains the method.

## Parts

| | Part | LCSC | Package | PCBA type | Stock / price |
| --- | --- | --- | --- | --- | --- |
| Charger | BQ24074RGTR | **C54313** | QFN-16-EP 3×3 | **Economic and Standard** | 3,691, ~$2.13 @1 |
| Boost | TPS61023DRLR | **C919459** | SOT-563 | **Economic and Standard** | — |

**Both parts qualify for Economic assembly**, confirmed on their JLC part-detail
pages. The assembly split in the platform spec holds: SMT everything on one
side, economic service, hand-solder the connectors and the Seed headers.

**Library type — Basic, Preferred or Extended — is not published** on either
page, and JLC's component search is a client-side app that returns "0 found" to
anything that fetches it rather than runs it. That is a scraping artefact, not
evidence about the part; the part-detail pages are proof enough that both are
stocked.

Both are near-certainly **Extended** — a Li-ion charger and a specific boost are
not parts a machine keeps loaded — which means a per-unique-part setup fee,
around $3 each. It resolves itself the moment a BOM is uploaded, since JLC
prices the fee there. **Not worth blocking on**, but it belongs in the estimate.

**The charger has an exposed pad.** QFN-16-EP needs thermal vias under it and a
segmented paste aperture, not one big opening.

**Two mask-tented thermal vias, not four.** Four Ø0.70 pads at (±0.45,±0.45)
consume 2.545 mm² of a 2.822 mm² exposed pad once each is tented, leaving 10%
solderable — the array was incompatible with an EP this size unless the vias
were resin-filled, which is a fab option and a cost. Two vias on the centreline
at (0,±0.45) leave 42.9% of the EP open in two 0.36 × 1.68 mm strips clear of
the tents, with paste inset to 74% of that opening. No paste lands on a barrel.
See `tools/fix_ep_thermal.py`.
 It is also the part
carrying charge current, so the pad is doing thermal work, not just mechanical.