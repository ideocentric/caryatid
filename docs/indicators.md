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
5.2 V boost rail. The switch asserts the boost's EN; the boost comes up; the
lamp lights. Off means genuinely off, with no firmware in the loop.

The lamp is a **3–9 V rated variant, so its current limiting is internal**:
`R_LED` is a 0 Ω link. Keep the 0603 footprint so a different switch can be
dropped in without a board change. At 5.2 V it runs slightly below the 4×AA
(~6 V) reference the brightness was judged against — expect roughly 80% of the
current, which the eye reads as near-identical. Worth a meter across the lamp at
both voltages before committing the panel.

**2. Charge LED — charge state, hardware only.** Driven directly from the
bq24074's open-drain `/CHG` and `/PGOOD` off the OUT rail, via J4. **This is the
indicator that satisfies the charge-complete-while-off requirement**, and it is
the only one that must exist. Nothing about it depends on firmware running.

**3. RGB — everything else, firmware driven.** J12, on D26/D27/D29. Solid on/off
mixing only; no PWM.

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

| `/CHG` | `/PGOOD` | Level |
| --- | --- | --- |
| high-Z | high-Z | 3V3 — idle, on battery |
| low | high-Z | charging |
| high-Z | low | external power, not charging |
| low | low | charging with external power present |

**The resistor values need choosing for margin, not convenience.** The obvious
first pick puts two of the four states about 150 mV apart, which a 12-bit ADC
resolves but which leaves nothing for tolerance or noise. Spread them across the
range and confirm the worst-case gap against resistor tolerance before layout.

This also delivers requirement P-8 — charge state exposed to the MCU, not only
to LEDs — which had no implementation before.

## What is deliberately not here

**No PWM on the RGB.** Solid mixing only. Seven states is enough, and dimming a
status LED on a stage instrument is a feature nobody has asked for.

**No firmware involvement in the power lamp.** It follows the rail. A power
indicator that depends on software is a power indicator that lies during a hang.