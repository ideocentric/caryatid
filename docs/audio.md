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

Size the resistor on the bench with the actual capsule, and lay the position out
as a divider so either arm can become a link.

**Confirm what drives the Seed's `AUDIO OUT`** — the WM8731 has both line and
headphone outputs and the Seed's documentation calls its pins line level, but
which codec output is actually routed there is worth reading off the Seed
schematic before relying on the drive capability.

## Input

Laid out on every board, DNP where unused. The complication is which capsule is
on the other end.

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

All three footprints are laid out; one set is populated.

**Electret** — the common case in anything from the 1980s on. A 2.2 kΩ from
3V3A to the capsule and an AC coupling capacitor into the codec. Draws well
under a milliamp. This is the path the platform spec already anticipated.

**Carbon** — the vintage case, and the awkward one. A carbon capsule is
effectively an amplifier: it modulates a DC current rather than generating a
signal, so it needs that current to exist. A real phone gave it tens of
milliamps from the line. Provisions:

- A **lower-value series resistor** from the 5 V rail rather than 3V3A, on its
  own footprint, sized on the bench. Expect single-digit-to-tens of mA.
- **An attenuator on the way out.** Carbon capsules are loud — output can be
  orders of magnitude above an electret, and will overload an input expecting
  mic level. Lay the pad out; populate it once measured.
- **Gate the current with the hook switch.** See below; this one matters.

**Dynamic** — no bias, and it needs gain the line input will not provide.

### The gain stage — one footprint, all three outcomes

**U4 = MCP6002 dual op-amp**, SOIC-8, `C116706`, powered from `3V3A`. Laid out
DNP with a bypass, so the capsule question can be answered *after* the boards
arrive rather than before the gerbers go out. This is the whole point: it
converts an unknown into a population choice.

| Capsule | Populate | Gain needed |
| --- | --- | --- |
| Carbon | **bypass**, possibly a pad | ~×3, or attenuation |
| Electret | stage + bias resistor | ~×100 (40 dB) |
| Dynamic | stage at maximum, no bias | ~×1000 (60 dB) |

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

#### Bypass as a divider, not a link

The proposal called for a 0 Ω bypass. **Lay it out as a two-resistor divider
instead** — 0 Ω plus an open position. A carbon capsule may run *hotter* than
line level, in which case the requirement is attenuation rather than a straight
pass. Fit 0 Ω and leave the shunt open for a true bypass; fit both for a pad. One
extra footprint, and it is the difference between a working input and a clipped
one.

#### Use the dual, lay out both channels

The Seed has `AUDIO IN L` and `AUDIO IN R`. A handset mic is mono, but caryatid
serves three instruments and stereo line-in is a plausible future need. A dual
op-amp is one package instead of two, so **both channels get the full network,
DNP**. A mono build populates one.

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