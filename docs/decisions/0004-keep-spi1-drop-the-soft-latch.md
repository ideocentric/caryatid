# 0004 — Keep SPI1 whole; drop the soft-latch

- **Status**: Accepted
- **Date**: 2026-08-08

## Context

The map was one pin short of everything it wanted, and the shortfall was found
by checking libDaisy's peripheral tables rather than a pinout card.

**SPI1's clock is only available on two pins**: `PG11` (D8) and `PA5` (A7).
A7 is an analogue panel input, so **D8 is the only free SPI1 clock on the
board.** An earlier draft of this map put the RGB LED's red channel on D8 — on
the stated grounds that it *freed* SPI1, which was exactly backwards. It would
have left D9/D10 as MISO and MOSI with no clock to drive them: not a bus, just
two pins.

Fixing that needed one more pin than the map had.

## Decision

**Drop the soft-latch** (power hold-out and button sense, formerly D29/D30), and
spend the released pins on the RGB, keeping D8/D9/D10 together as a complete
SPI1 expansion port.

The soft-latch is redundant. The committed power control is an illuminated
mechanical latching switch, which holds its own state without help. Soft-latch
and a latching switch are alternatives, not complements — the original spec
marked the soft-latch optional in both its pin map and its connector table.

Resulting allocation:

| | Pins |
| --- | --- |
| RGB status | D26, D27, D29 |
| Expansion / SPI1 | D8 SCLK, D9 MISO, D10 MOSI, D30 CS |

## Consequences

**Good:**

- A display, port expander, SD card or external DAC stays a daughterboard rather
  than a board revision.
- The RGB sits on three plain GPIOs and sacrifices no peripheral.
- D30 is a genuine spare and doubles as the expansion chip select.

**Bad:**

- **No soft power control.** Firmware cannot cut its own power, and cannot
  intercept a power-down to save state. Any build wanting that needs these pins
  back, and would have to take them from the RGB.
- The board is now fully allocated. D30 is the only unassigned pin.

**Neutral:**

- SPI1's chip select can be any GPIO; D7 and A8 are its hardware NSS options but
  software CS on D30 is expected.