# Audio

Output is straightforward. Input is not, because one of the instruments plugs a
telephone handset into it and a handset is not a microphone in any sense the
codec expects.

## Output

Stereo line out on jacks, through the Pod-style coupling network. Populated on
every build.

**A telephone earpiece must not be driven from the line output.** A receiver
capsule is roughly 50–300 Ω where a line output expects to see 10 kΩ or more.
Two things go wrong at once: the output is loaded far below what it is designed
for, and the DC-blocking capacitor forms a high-pass with that low impedance
that removes most of what little bass a handset had.

**A series resistor solves both problems at once**, which is the neat part.
Put 1 kΩ in series with a 150 Ω earpiece and the output sees 1.15 kΩ instead of
150 Ω — nearly eight times easier — while the earpiece gets about 13% of the
voltage, which is the attenuation it needed anyway. A telephone receiver is far
more sensitive than headphones and is painfully loud at anything like line
level.

**So caryatid needs no headphone amplifier**, and does not have one. An earlier
draft of this document said to drive the earpiece from "the headphone output",
which assumed an amplifier this board does not carry. Correcting it: the Seed's
`AUDIO OUT` through a series resistor is the whole circuit.

**R47 and R49, 1 kΩ, are that resistor, and they are the whole attenuator.**
The position used to be laid out as a divider — R48/R50 as an open shunt arm, so
either arm could become a link once a capsule was measured.
[ADR 0010](decisions/0010-nothing-is-dnp.md) deleted the shunt arm: `open` is
not a value anyone can ship, and the series arm is what the argument above
actually calls for. If a measured earpiece wants a different ratio, change R47
and R49, or use the codec's own output volume.

**Confirm what drives the Seed's `AUDIO OUT`** — the WM8731 has both line and
headphone outputs and the Seed's documentation calls its pins line level, but
which codec output is actually routed there is worth reading off the Seed
schematic before relying on the drive capability.

## Input

**Both channels are populated on every board, and each is selected by three
jumpers** — see [ADR 0009](decisions/0009-mic-input-is-jumper-selected.md) for
the left and [ADR 0010](decisions/0010-nothing-is-dnp.md) for the right. The
complication is which capsule is on the other end, and the board no longer needs
that answered before it is built.

| Jumper | | Selects | Positions |
| --- | --- | --- | --- |
| **JP1** | **JP4** | capsule bias | `1-2` 2k2 to 3V3A · none · `2-3` 220R to 5 V |
| **JP2** | **JP5** | signal path | `1-2` op-amp · `2-3` bypass |
| **JP3** | **JP6** | gain leg | `1-2` 1k (×101) · `2-3` 392R (×256) |

**JP1–JP3 are the left channel, JP4–JP6 the right**, and the two sets are
identical — same positions, same meanings, same procedure. A handset mic is
mono and uses the left; a stereo pair or two different elements uses both.

| Capsule | bias | path | gain |
| --- | --- | --- | --- |
| **Electret** | `1-2` | `1-2` | `1-2` |
| **Dynamic** | — | `1-2` | `2-3` |
| **Carbon** | `2-3` | `2-3` | — |

**[mic-configurations.md](mic-configurations.md) draws all three**, with the
signal path for each and a diagram of the shunt positions.

**The table is on the silkscreen beside the jumpers**, with the DC-resistance
test printed next to it, so the board carries its own procedure. `12` and `23`
are pin pairs rather than positions, because "top" depends on which way the
board is held; the jumpers stand vertically with pin 1 uppermost.

> **This replaced a DNP-and-solder design.** The front end used to be laid out
> DNP with the capsule chosen by populating one of three mutually exclusive
> sets — a soldering iron, after measuring. The requirement that it be
> selectable *after* assembly was never written down, so the board was built
> against a different one. ADR 0009 has the full account.
>
> **And it replaced it twice.** ADR 0009 fixed the left channel and left the
> right one DNP, which meant the right still carried the same two exclusive
> pairs — 2k2-to-3V3A against 220R-to-5V on `MIC_R`, op-amp output against raw
> bypass on `AUDIO_IN_R`. Populating it without jumpers would have shipped
> exactly the defect 0009 exists to prevent, so **"populate the right channel"
> and "the right channel works" were not the same instruction.** ADR 0010.

### Identify the capsule before choosing components

Three kinds turn up in handsets and they want incompatible circuits. **A DC
resistance measurement across the capsule tells you which you have**, and it
takes a minute:

| Reading | Capsule | What it needs |
| --- | --- | --- |
| ~50–300 Ω, unstable, changes when tapped | **carbon** | DC current through it, tens of mA |
| Open at DC, or reads as a capacitor | **electret** | bias resistor to a rail |
| ~150–600 Ω, stable | **dynamic** | no bias, and gain |

"Unstable and changes when tapped" is the carbon tell — the granules resettle,
and that variability *is* how the thing works.

### Provisions on the board

**All three paths are fitted; the jumpers choose between them.** The parts below
are on every board — what follows describes what each path does, not what to
solder.

**Electret** — the common case in anything from the 1980s on. A 2.2 kΩ from
3V3A to the capsule and an AC coupling capacitor into the codec. Draws well
under a milliamp. This is the path the platform spec already anticipated.

**Carbon** — the vintage case, and the awkward one. A carbon capsule is
effectively an amplifier: it modulates a DC current rather than generating a
signal, so it needs that current to exist. A real phone gave it tens of
milliamps from the line. Provisions:

- A **lower-value series resistor** from the 5 V rail rather than 3V3A, on its
  own footprint, sized on the bench. Expect single-digit-to-tens of mA.
- **Attenuation on the way out.** Carbon capsules are loud — output can be
  orders of magnitude above an electret, and will overload an input expecting
  mic level. **This is the codec's job, not a resistor's**: the WM8731 line PGA
  reaches −34.5 dB, adjustable at run time. The board used to carry a resistor
  pad here (R64/R66) and [ADR 0010](decisions/0010-nothing-is-dnp.md) removed
  it — a fixed pad chosen with a soldering iron is the thing this design is
  trying to stop doing.
- **Gate the current with the hook switch.** See below; this one matters.

**Dynamic** — no bias, and it needs gain the line input will not provide.

### The gain stage — one footprint, all three outcomes

**U4 = MCP6002 dual op-amp**, SOIC-8, `C116706`, powered from `3V3A`. **Fitted
on every board, both halves live**, with JP2/JP5 selecting whether each channel
goes through its amplifier or around it. That is the whole point: the capsule
question is answered *after* the boards arrive, and answered with a shunt rather
than an iron.

| Capsule | Path | Gain needed |
| --- | --- | --- |
| Carbon | **bypass**, PGA attenuates | ~×3, or attenuation |
| Electret | stage + bias resistor | ~×100 (40 dB) |
| Dynamic | stage at maximum, no bias | ~×1000 (60 dB) |

> **Where those three numbers come from**, which was missing until 2026-08-23:
> [`discovery/findings/mic-gain-budget.yaml`](../discovery/findings/mic-gain-budget.yaml).
> The target is the WM8731's own `VINLINE` of **1.0 Vrms at 0 dB**, and the
> sources are class-typical sensitivities: electret 5 to 17.8 mV/Pa, dynamic
> 1 to 4 mV/Pa, carbon hundreds of mV. Dividing gives 56–200×, 250–1000× and
> 2–10× respectively, and **all three targets above land inside their range**.
> The record is `unverified` regardless, because those are typical figures for a
> class and the mouthpiece SPL is an assumption. Nothing needs to change; it can
> now be checked.

#### Single supply needs a mid-rail bias — this is not optional

An op-amp on a single 3V3 rail has no negative supply, so an AC signal must sit
on a DC pedestal at half the rail or the negative half of the waveform clips off
entirely. Gain-set resistors alone will not work.

```
  3V3A ──[100k]──┬──────────────┐
                 │              │
               [10u]         + in
                 │              │
  GND ──[100k]───┘              │
                                │
  in ──[C_in]───────────────────┘

              ┌──[C_g]──[R_g]──┐
              │                │
  − in ───────┴────[R_f]───────┴── out ──[C_out]── to codec
```

- `R_b1`/`R_b2` 100 kΩ, `C_b` 10 µF — mid-rail reference at 1.65 V
- `C_in` 1 µF — blocks the capsule's DC, passes audio
- `R_f`/`R_g` set gain as `1 + Rf/Rg`
- **`C_g` in series with `R_g` is the one that gets forgotten.** Without it the
  stage has the same gain at DC as at audio, so the 1.65 V pedestal is amplified
  straight into the rail and the output sits jammed at one end. With it, DC gain
  is exactly 1 and the output rests at mid-rail where it belongs.
- `C_out` 10 µF — strips the pedestal back off before the codec

#### The gain ceiling, and where the last 12 dB comes from

The MCP6002 has 1 MHz of gain-bandwidth, so usable gain and bandwidth trade
directly:

| Gain | dB | −3 dB bandwidth |
| --- | --- | --- |
| ×100 | 40 | 10 kHz |
| **×294** | **49** | **3.4 kHz — the voiceband edge** |
| ×1000 | 60 | 1 kHz — voiceband lost |

**A dynamic capsule wants 60 dB, and one stage cannot give it** without
collapsing the bandwidth below the voiceband. The resolution costs nothing: the
WM8731's line input has its own PGA with gain as well as attenuation, so
**×250 in the op-amp plus the codec's own gain covers the dynamic case**.

**Confirmed 2026-08-21** against WM8731 `PD Rev 4.0` (Feb 2005), Table 3 —
`LINVOL[4:0]` at R0 (00h) and `RINVOL[4:0]` at R1 (02h):

> `11111` = **+12dB** . . 1.5dB steps down to `00000` = −34.5dB. Default
> `10111` = 0dB.

So the arithmetic holds: ×250 is 47.96 dB, plus 12 dB is **60 dB**, and at ×250
the MCP6002's 1 MHz gain-bandwidth product puts −3 dB at **4 kHz** — above the
3.4 kHz voiceband edge. The dynamic case is covered with margin to spare.

**The codec's larger reserve is confirmed unreachable, so do not plan around
it.** The same datasheet gives the WM8731's *microphone* path 14 dB nominal and
**34 dB** with `MICBOOST` set. **The Seed does not bring `MICIN` out**, checked
2026-08-21 against both `Seed_pinout.csv` and `ES_Daisy_Seed_Rev7.pdf`: pins
16–19 are `AUDIO_IN_L`, `AUDIO_IN_R`, `AUDIO_OUT_L`, `AUDIO_OUT_R` and there is
no mic pin on the 40-pin header at all. The line PGA's **+12 dB is the only
codec-side gain available.**

Nothing in the design changes — ×250 plus 12 dB already covered the dynamic
case with the bandwidth to spare. What changes is that there is **no hidden
headroom to fall back on**: if a capsule ever needs more than 60 dB, it has to
come from the op-amp stage or from a module ahead of the board, not from the
codec.

Carbon and electret are the likely outcomes anyway; a dynamic capsule in a
handset is the rarest of the three.

#### The bypass is a link, and the pad is in the codec

The proposal called for a 0 Ω bypass. This document then argued for a
two-resistor divider instead — 0 Ω plus an open shunt — because a carbon capsule
may run *hotter* than line level and want attenuation rather than a straight
pass. R63/R64 and R65/R66 were built that way.

**[ADR 0010](decisions/0010-nothing-is-dnp.md) took the shunt arms out**, and
the reason is the same one that put the jumpers in. The requirement is real, but
a resistor pad answers it *once, with a soldering iron, before you have heard
the capsule*. The WM8731's line PGA answers it at run time and goes further than
a pad would have been asked to: **−34.5 dB**, in 1.5 dB steps, per channel.
R63 and R65 remain as the 0 Ω link.

The two costs of that, stated plainly: a source hot enough to clip the codec's
input *before* the PGA is not helped by the PGA, and the fix is then a resistor
in the loom rather than on the board. And R66 was on the wrong node anyway —
it tapped `AUDIO_IN_R`, downstream of where JP5 now lands, so it would have
padded the op-amp output as well as the bypass.

#### Use the dual, lay out both channels

The Seed has `AUDIO IN L` and `AUDIO IN R`. A handset mic is mono, but caryatid
serves three instruments and stereo line-in is a plausible future need. A dual
op-amp is one package instead of two, so both channels are laid out. **Both are
fitted and jumper-selected**, and they are identical: either channel takes any
of the three capsule types.

> **The right channel was DNP until ADR 0010, and this paragraph used to say so.**
> ADR 0009 argued that capsule selection was meaningless on a line-in channel.
> That was true of the *use* and irrelevant to the *board*: the right channel is
> laid out as an exact mirror of the pre-jumper left, so it inherited both
> mutually exclusive pairs whether or not anyone intended to plug a capsule into
> it. The asymmetry is gone and the two channels now share one procedure.

**R59/R60/R61 change meaning without changing value.** They were populated by
ADR 0009 for a defensive reason — U4 is a dual, and populating it for the left
channel alone would have left section B's inputs floating, which oscillates and
draws current, so R59/R60 biased it to mid-rail and R61 closed the loop with R62
open, making it a unity-gain follower at `VBIAS_R`. With R62 and JP6 in circuit
those same three parts are now the working mid-rail reference and feedback
resistor of a live channel. **What was a muzzle is now the circuit.**

#### The fallback lands on the bypass path

If the vintage element sounds bad or is dead, gutting the housing and hiding a
modern electret capsule or a **MAX9814** AGC module inside keeps the look and
gives a known-good signal. Worth noting the MAX9814 outputs near line level with
its own AGC, so it uses the **bypass** — the board does not change for it. Every
branch of this decision, including the escape hatch, lands on the same footprint
set.

### Gate the mic bias with the hook switch, in hardware

A carbon capsule drawing tens of milliamps continuously is a real fraction of a
battery instrument's budget, and it is pure waste on-hook.

**A telephone hook switch has more than one pole.** Use one for the logic —
into the 74HC14 and on to D7 — and a second to physically break the mic bias.
Then the current only flows off-hook, it costs no GPIO, and it keeps working if
the firmware hangs. The bias return leaves on **J14**, so it is either a link
to ground there or a wire out to the switch's second pole. (J14 is the number
the soft-latch vacated when [ADR 0004](decisions/0004-keep-spi1-drop-the-soft-latch.md)
dropped it.)

**`MIC_RTN` is shared by both channels** — one return on J18 pin 3, two
capsules. That is the correct arrangement, because the gate belongs to the
handset rather than to a capsule: lifting the handset should energise whatever
is in it. It does mean a stereo *carbon* pair would put both bias currents
through the one switch contact, which is worth knowing before anyone sizes it.

Firmware still gates the *audio path* from D7. That is a musical decision and
belongs in software. This is about current, and belongs in copper.

### The codec's mic path is not available, and that reshapes the input

The WM8731 has a microphone input with its own bias generator and a boost stage,
which would have made the electret case nearly free. **libDaisy does not use
it.** In `dev/codec_wm8731.cpp` the initialisation routes the ADC to line
(`CODEC_ADC_LINE`), mutes the mic (`CODEC_MIC_MUTE`), and **powers the mic block
down** (`CODEC_POWER_DOWN_MIC`).

So the input is a **line input**, and the consequences invert the obvious
expectation:

- **An electret is the awkward case, not the easy one.** Its output is
  mic-level, going into an input scaled for line level, with only the line PGA's
  small gain available. Expect it to be quiet and to need external gain — a
  single-transistor or op-amp stage on the input network, which is a footprint
  that has to exist before layout, not after.
- **A carbon capsule may suit the line input directly.** It modulates a
  substantial DC current and its output is orders of magnitude above an
  electret's. The vintage part is the one that fits what the Seed actually
  gives you — it may want a pad rather than a preamp.

Two things still to confirm, and both change the input network rather than
merely inform it:

1. **Does the Seed route `MICIN`/`MICBIAS` to a pin at all?** libDaisy powering
   the block down suggests not, but that is inference from a driver, not from a
   schematic. If the pins are there, re-enabling the mic path is a firmware
   change and the electret becomes easy again. **Check the Seed schematic.**
2. **Measure the capsule** before choosing between a preamp footprint and a pad
   footprint. Lay out both; populate one.

## Not addressed here

**Sidetone.** A real telephone feeds a little of the mic back to the earpiece so
the handset does not feel dead. Doing it in firmware is trivial and doing it in
hardware is a hybrid coil. It is a musical choice for the instrument, not a
platform feature, and it needs no board provision.