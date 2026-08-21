# 0009 — The mic input is jumper-selected, not solder-selected

- **Status**: **Accepted 2026-08-21.** Blocking fabrication — the board is not
  ordered until this is implemented.
- **Date**: 2026-08-21
- **Amends**: the input half of [audio.md](../audio.md). The output, the capsule
  identification table and the gain arithmetic all stand unchanged.

## Context

**The requirement was never written down, and the board was built without it.**

The intent was that caryatid support all three handset capsule types *without
rework* — that which circuit is active should be selectable after assembly, by
the person holding the instrument, not fixed by which resistors an assembler
soldered.

What was built instead: one input socket, J18, with the entire front-end laid
out **DNP**, and the capsule type chosen by populating one of three mutually
exclusive sets. The netlist shows why they are exclusive:

```
/audio/MIC_L     J18.1  R51.2  R52.2  R63.1  C23.1
                 R51.1 -> +3V3A   (2k2,  electret bias)
                 R52.1 -> +5V     (220R, carbon bias)

AUDIO_IN_L       A1.16  C25.2  R63.2  R64.1
                 C25.1 -> op-amp output
                 R63.1 -> raw MIC_L (bypass)
```

Fitting both bias resistors puts 2k2 to 3V3 against 220R to 5 V on the capsule.
Fitting both output paths shorts the op-amp output to the raw capsule signal. So
the design is genuinely one-of-three, decided with a soldering iron.

**This is a documentation failure before it is a design failure.** The
requirement is absent from `audio.md`, from `connectors.md`, from every ADR and
from the schematic history. Everything downstream was built consistently against
a different, written requirement. Nobody drifted; the input was never captured.

## Decision

**Three jumpers on the left channel select the capsule circuit**, and the mic
front-end is **populated at assembly** rather than left DNP.

| Jumper | Selects | Positions |
| --- | --- | --- |
| **JP1** bias | capsule supply | `3V3A` (2k2) · `OFF` · `5V` (220R) |
| **JP2** path | signal route | `AMP` · `BYPASS` |
| **JP3** gain | R58 leg | `x101` (1k) · `x256` (392R) |

| Capsule | JP1 | JP2 | JP3 | Result |
| --- | --- | --- | --- | --- |
| **Electret** | 3V3A | AMP | x101 | 40.1 dB, −3 dB at 9.9 kHz |
| **Dynamic** | OFF | AMP | x256 | 48.2 dB + 12 dB codec = **60.2 dB**, 3.9 kHz |
| **Carbon** | 5V | BYPASS | — | passive, through the pad |

Gain is `1 + R57/R58` on the existing non-inverting stage. **One op-amp
configuration serves both amplified cases** — same topology, same mid-rail bias,
same coupling; only the gain leg changes. Carbon needs no active stage at all.

**Left channel only.** A handset mic is mono. The right channel keeps its DNP
network for a future stereo line-in build, where capsule selection is meaningless.

**Populating U4 pulled C30 in with it, and that was nearly missed.** `C30` is
the only decoupling capacitor on `+3V3A`, and it was DNP — correctly, while
nothing active sat on that rail. Fitting the op-amp made it mandatory, and it
was not on the original populate list. Caught by tracing what `+3V3A` actually
feeds, not by any check: **an undecoupled supply is not a DRC violation, an ERC
violation, or a parity error.**

*The general rule this is an instance of:* clearing DNP on an active part makes
its support components mandatory, and they are usually DNP for the same reason
it was. Trace the supply rails after any such change.

## Why jumpers rather than three sockets

The original idea was three sockets, one per capsule type, selected by which one
you plug into. That is attractive — **the user becomes the detector**, with no
firmware, no analogue mux and no ambiguous measurement. It deserves recording as
the alternative it is.

It was rejected for one reason: **summing**. Three front-ends feeding one
`AUDIO_IN_L` means two idle stages sitting at VMID inject their noise into the
active one, and fixing that needs switched-contact jacks, an analogue mux (which
wants a GPIO, and `D30` is the only spare) or series resistors and a tolerance
for the noise.

**A jumper connects exactly one path at a time**, so the problem does not arise.
That is the whole of the argument.

All three capsules are **2-terminal unbalanced devices on identical wiring**, so
three sockets would have been three *identical* connectors — the differentiation
was never in the connector. That is what makes one socket plus a selector
equivalent, and cheaper.

## Consequences

**Good:**

- The board arrives working. No rework, no soldering iron, no waiting on a
  capsule measurement before ordering.
- The capsule question genuinely moves to run time, which was the intent.
- No summing problem, no extra connectors, no GPIO spent.
- One MCP6002 still covers it; carbon needs no active stage.

**Bad — real, not formalities:**

- **A jumper is mis-settable in a way that plugging into the right hole is
  not.** JP1 on `5V` with an electret fitted puts 220R to 5 V into it. JP1 on
  `OFF` with an electret gives silence. Neither harms the board; the first could
  stress a capsule.

  *Mitigation:* the silkscreen carries the identification test beside the
  positions, so the legend **is** the procedure — `OPEN=ELECTRET`,
  `50-300R UNSTABLE=CARBON`, `150-600R=DYNAMIC`.
- **The mic front-end is no longer DNP**, so it is assembled on every board
  whether or not that instrument uses a mic. ~15 parts plus U4, and U4 is an
  Extended part carrying its own loading fee.
- **Dynamic costs bandwidth.** At x256 the MCP6002's 1 MHz GBW puts −3 dB at
  3.9 kHz. That covers the 300–3400 Hz voiceband with little margin and would
  not suit a wideband source. Electret keeps 9.9 kHz, which is why JP3 exists.
- **This delays fabrication.** The board was verified and ready to order.

**Neutral:**

- The right channel is untouched and stays DNP, so the two channels are
  deliberately asymmetric. Recorded so it is not read as an oversight later.

## What this does not fix

`MIC_RTN` still leaves via J18 pin 3 and pairs with J14 to the hook switch's
second pole, so the **carbon bias is gated in hardware** as before. Electret and
dynamic builds tie `MIC_RTN` to ground in the loom. JP1 does not change that,
and should not: gating tens of milliamps on-hook is worth a wire.