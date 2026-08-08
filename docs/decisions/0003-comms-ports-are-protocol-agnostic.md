# 0003 — Comms ports carry signals, not protocols

- **Status**: Accepted
- **Date**: 2026-08-08

## Context

Different builds want different links to the outside world: an I2C distance
sensor, TRS MIDI in, an ESP32 bridge speaking OSC over UART. Freezing a pin map
around any one of them would make the others a board revision.

The original spec named D11/D12 "I2C". That name was the problem.

## Decision

Treat those pins as a **comms port**: two signal lines whose protocol is decided
by what is plugged in and a line of firmware config.

This works because of a fact about the silicon rather than a convention:
**D11/D12 (PB8/PB9) are simultaneously I2C1 and UART4.** The same two pins are
SCL/SDA or RX/TX depending only on how they are configured.

- **Port A** — D11/D12. I2C1 or UART4.
- **Port B** — D13/D14. USART1. Competes with SW1/SW2.

Port A gets two footprints on the same pins: a 4-pin JST-SH on the
Qwiic/STEMMA-QT pinout, and a 6-pin JST-PH module port carrying both rails and
an AUX line. One is populated.

Protocol-specific circuitry — a MIDI input opto-isolator, a level shifter, a
radio — belongs on the daughterboard, not on this PCB.

## Consequences

**Good:**

- MIDI, I2C and an OSC bridge are the same connector. A new link is a
  daughterboard, not a board spin.
- Off-the-shelf Qwiic sensors are a cable rather than a breakout to design.
- The platform stays free of circuits most builds would not populate.

**Bad:**

- **Two ports is the ceiling.** There is no third UART on free pins.
- Port B costs SW1 and SW2. A build wanting three switches and two comms ports
  cannot have both — which is why loa's hook switch is on SW3/D7, so that
  choosing port B later does not require moving a panel control.
- Firmware must know what is plugged in; the board cannot tell it.