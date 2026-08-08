# 0005 — Indicators span two power domains, so there are three of them

- **Status**: Accepted
- **Date**: 2026-08-08

## Context

The wanted behaviour was one RGB LED showing battery low, charging, fully
charged and fault. It cannot be done with one LED on Seed GPIOs, and the reason
is physical rather than a matter of taste.

**Charging happens while the instrument is switched off.** Seed GPIOs are dark
when the Seed is unpowered, so charging and charge-complete — the two states
most worth seeing while the thing sits on a bench overnight — are exactly the
two a firmware-driven LED cannot show.

A shared LED driven by both the charger and the Seed was considered. It needs a
low-side transistor per channel with a diode-OR on each gate, and it has a real
hazard: an LED cathode tied to an unpowered Seed GPIO forward-biases that pin's
ESD diode and back-powers the chip through the LED resistor.

## Decision

Three indicators, split by what has to work without firmware:

| | Shows | Driven by |
| --- | --- | --- |
| Switch lamp | power on/off | the 5.2 V rail, no firmware |
| Charge LED (J4) | charging, charge complete | `/CHG`, `/PGOOD`, no firmware |
| RGB (J12) | battery, fault, and charge state while awake | firmware |

Charge status is also fed back to the MCU on **A11**, as `/CHG` and `/PGOOD`
encoded into four voltage levels on one analogue pin, because the digital budget
had no room for two inputs. This delivers loa's P-8, which had no implementation
before.

## Consequences

**Good:**

- The indicator that must work with no firmware running does not depend on
  firmware.
- No shared drivers, so no back-powering path exists to get wrong.
- The RGB can still show charge state while the instrument is on, from A11.

**Bad:**

- Three indicators on the panel rather than one. This is the cost of the
  requirement, not of the design.
- The A11 encoding needs its resistor values chosen for margin — the obvious
  first pick leaves two states about 150 mV apart.

**Neutral:**

- The RGB is solid on/off mixing, no PWM. Seven colours, urgency in the blink
  rate, and off means fine.