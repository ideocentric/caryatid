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

**Drive it from the headphone output instead.** loa's requirement A-2 already
asks for a headphone amplifier that can drive 32 Ω; a 150 Ω earpiece is an
easier load than the one the part was chosen for. Then attenuate — a telephone
receiver is far more sensitive than headphones and will be painfully loud at
anything like normal level. A series resistor sized on the bench, with the pad
laid out as a divider so either arm can be a link.

This is a **loa population choice, not a board change**: the headphone output
exists regardless, and whether it goes to a jack or to a handset is a loom
question.

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

### Gate the mic bias with the hook switch, in hardware

A carbon capsule drawing tens of milliamps continuously is a real fraction of a
battery instrument's budget, and it is pure waste on-hook.

**A telephone hook switch has more than one pole.** Use one for the logic —
into the 74HC14 and on to D7 — and a second to physically break the mic bias.
Then the current only flows off-hook, it costs no GPIO, and it keeps working if
the firmware hangs. The board provides a two-position footprint for the bias
return so it is either a link to ground or a wire out to the second pole.

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