# Indicators

Three indicators, and the reason there are three rather than one is a power
domain problem, not a design preference.

## The constraint

**Charging happens while the instrument is switched off.** The RGB LED hangs on
Seed GPIOs, and those are dark when the Seed is unpowered. So of the four states
worth showing, two cannot come from firmware at all:

| State | Needs the Seed powered? |
| --- | --- |
| Battery low while playing | yes — fine |
| Fault / warning | yes — fine |
| **Charging** | **no** |
| **Charge complete** | **no** |

Anything that must be readable with the instrument off has to be driven by
hardware. That is the whole argument.

## The three

**1. Switch lamp — power state.** The illuminated latching switch, fed from the
**5.0 V** boost rail. The switch asserts the boost's EN; the boost comes up; the
lamp lights. Off means genuinely off, with no firmware in the loop.

The lamp is a **3–9 V rated variant, so its current limiting is internal**:
`R_LED` is a 0 Ω link. Keep the 0603 footprint so a different switch can be
dropped in without a board change.

At 5.0 V it runs below the 4×AA (~6 V) reference the brightness was judged
against — if the limiting is a plain series resistor, roughly 75% of the
current, which the eye reads as around 85% as bright. Almost certainly
indistinguishable, and comfortably inside a range the lamp already sees on
depleted NiMH. **Worth a meter in series at both voltages before committing the
panel**, since it is two minutes now against a board spin later.

**2. Charge LED — charge state, hardware only.** Driven directly from the
bq24074's open-drain `/CHG` and `/PGOOD` off the OUT rail, via J4. **This is the
indicator that satisfies the charge-complete-while-off requirement**, and it is
the only one that must exist. Nothing about it depends on firmware running.

**3. RGB — everything else, firmware driven.** J12, on D26/D27/D29. Solid on/off
mixing only; no PWM.

> **It cannot be driven from a 3V3 GPIO.** Green and blue have forward voltages
> around 3.0-3.1 V against an output-high of roughly 3.15 V — they will not
> light, and no resistor value fixes it. **Common anode to the 5 V rail with the
> GPIOs sinking** — all three pins verified `FT`. See [values.md](values.md).

## RGB states

Seven colours from on/off mixing, urgency carried by blink rate, and **off means
fine** — which is what you want on a stage.

| Condition | Colour | Pattern | Source |
| --- | --- | --- | --- |
| Playing, battery OK | off | — | — |
| Battery low — head for a socket | amber | slow, 1 Hz | A10 |
| Battery critical | red | fast, 4 Hz | A10 |
| Fault | magenta | fast, 4 Hz | A10 + A11 |
| Charging | blue | solid | A11 |
| Charge complete | green | solid | A11 |

Cyan and white are deliberately unassigned. A spare state is worth more than an
exhaustive palette.

Firmware can show charge state on the RGB *while the instrument is on* because
it reads charge status from A11 — that is a convenience, not the mechanism that
satisfies the off-state requirement.

## Faults worth signalling

Magenta means something specific, or it means nothing:

- charger thermal fault or charge-timer expiry, via the `/CHG` behaviour on A11
- cell voltage critically low, via A10
- **cell disconnected or its protection tripped** — A10 reads near zero while
  the OUT rail is alive. Worth catching before a gig rather than during one.

## Charge status on one analogue pin

`/CHG` and `/PGOOD` are both open-drain, and the pin budget had no room for two
digital inputs. A11 had no other job, so both signals are encoded onto it as
four voltage levels: a pull-up to 3V3 and two different-valued pull-downs.

```
        3V3 ──[ 10k ]───┬──[ 1k ]──┬── A11
                        │          │
        /CHG ──[ 10k ]──┤        [10nF]
                        │          │
      /PGOOD ──[ 20k ]──┘         GND
              (2 x 10k series)
```

**Four resistors of one value** — the 0.1% 10 k already in stock (C374544).

| `/CHG` | `/PGOOD` | State | Level | Counts |
| --- | --- | --- | --- | --- |
| high-Z | high-Z | idle, on battery | 3.300 V | 4095 |
| high-Z | low | external power, not charging | 2.200 V | 2730 |
| low | high-Z | charging | 1.650 V | 2048 |
| low | low | charging, external present | 1.320 V | 1638 |

Minimum separation **330 mV** — 409 ADC counts — and because the parts are 0.1%
the worst case is **329 mV**, which is to say the nominal.

**Decode by nearest level, not by thresholds.** The bands cannot be confused, and
nearest-neighbour needs no constants that can later drift out of date.

### How the values were arrived at

A search over E24 maximising the minimum separation gives **10 k / 11 k / 18 k**
and 390 mV, against roughly 150 mV for the naive first pick. Monte-Carlo over
tolerance showed that network holding up well:

| Tolerance | Worst gap | Bands overlap |
| --- | --- | --- |
| 1% | 377 mV | no |
| 5% | 312 mV | **no** |

That the scheme still works at 5% is what made the substitution safe: **trading
390 mV for 330 mV buys two fewer SMT feeders and a part already on the shelf.**
See [sourcing.md](sourcing.md).

Two things that are not obvious either way:

- **The levels depend only on the ratios**, so the network scales freely. 10 k is
  the largest value that keeps the ADC source impedance sane; scaling down only
  burns current for nothing.
- **The pull-up sits on 3V3, the Seed's rail**, so the network draws nothing
  while the instrument is off. The charger's status pins are alive then, but with
  no pull-up there is no path. Unlike the A10 battery divider, this costs no
  standby current at all.

`1k + 10nF` mirrors the A10 filter, and the capacitor is doing real work: at 10k
source impedance the ADC's sample-and-hold cannot charge fast enough on its own,
so the cap supplies it and the 10k merely tops the cap back up between samples.
**Use a long ADC sample time on A11 regardless.**

This also delivers requirement P-8 — charge state exposed to the MCU, not only
to LEDs — which had no implementation before.

## What is deliberately not here

**No PWM on the RGB.** Solid mixing only. Seven states is enough, and dimming a
status LED on a stage instrument is a feature nobody has asked for.

**No firmware involvement in the power lamp.** It follows the rail. A power
indicator that depends on software is a power indicator that lies during a hang.