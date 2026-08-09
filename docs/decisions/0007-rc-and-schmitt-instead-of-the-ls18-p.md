# 0007 — RC and a Schmitt trigger instead of the LS18-P

- **Status**: Accepted
- **Date**: 2026-08-09

## Context

The platform spec specified an **LS18-P** switch debouncer: a purpose-built
part, three channels, proven on the fabricated absonus board, with a symbol and
footprint already drawn.

It is also **PDIP and socketed**. On a board whose stated assembly model is "SMT
one side by machine, hand-solder only the connectors", it is two hand operations
per board — the socket and the part — for a function that is not hard.

The switches also do not sit at the pin. They arrive on JST leads from a panel,
which is a length of unshielded wire acting as an antenna into a logic input.

## Decision

Replace it with **RC filtering into a 74HC14** hex Schmitt-trigger inverter
(SOIC-14, `C5605`). Per channel: a 10 kΩ pull-up, 10 kΩ in series, and a
capacitor to ground.

- The RC suppresses both contact bounce and cable-borne noise.
- The Schmitt input restores a clean edge from the slow ramp, which a plain
  logic input could not.
- The package is SMT, so the whole thing moves to the machine side.

**The capacitor is a per-channel population choice**, not a fixed value: 220 nF
for a panel switch, 1 µF for a telephone hook lever. 100 nF gives 1.2 ms and is
below typical bounce.

**Unused inputs (9, 11, 13) are tied to ground.**

## Consequences

**Good:**

- The hand-solder list loses a part and a socket, and nothing on this sheet
  needs a custom symbol any more — the 74HC14 is stock KiCad.
- Cable noise is filtered, which the LS18-P sitting behind a metre of panel loom
  was not doing.
- The debounce interval becomes a per-instrument choice rather than whatever the
  IC decided.
- Basic-tier part at a few cents against a specialist one.

**Bad:**

- Nine more passives, three per channel, where the LS18-P needed none.
  Machine-placed 0603s, so the cost is board area rather than labour.
- It discards a part proven on absonus, and its symbol and footprint with it.
- Each closed switch draws **330 µA** through its pull-up. Negligible against a
  250 mA instrument, but not zero on a build with latching switches that sit
  closed.

**Neutral, and worth stating plainly:**

- **The output is inverted, and that is the safer polarity, not a defect.** With
  a pull-up and a switch to ground, an unplugged cable reads identically to
  "switch open" — for loa that means on-hook, so a broken lead leaves the
  instrument silent with the mic bias off. Restoring the polarity with a second
  inverter would spend three of the spare gates to buy the opposite failure: a
  broken lead reading as off-hook with audio live. Firmware inverts a bit for
  free.
- **Six gates does not mean six usable channels.** The Seed map is fully
  allocated with `D30` the only spare, so three surplus inverters have nowhere
  to go. They are headroom for a future revision, not capacity today.