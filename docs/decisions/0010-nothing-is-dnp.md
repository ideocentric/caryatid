# 0010 — Nothing is DNP

- **Status**: **Accepted 2026-08-21.** Blocking fabrication — the board is not
  ordered until this is implemented.
- **Date**: 2026-08-21
- **Extends**: [ADR 0009](0009-mic-input-is-jumper-selected.md), which made the
  left mic channel jumper-selected and explicitly left the right channel DNP.
  That carve-out is withdrawn here.
- **Amends**: the input half of [audio.md](../audio.md) again, and the
  Population section of [panel-io-sheet.md](../panel-io-sheet.md).

## Context

**DNP was an instruction to a person, and there is no longer a person.**

`hardware/README.md` has said the honest version of this for a while: when the
connectors were hand-fitted, "DNP" meant "I will decide later" and cost nothing.
Since JLCPCB fits the through-hole parts too, every DNP line is either a part
paid for and not wanted, or a part wanted and not fitted — and finding out which
happens when the boards arrive.

Sixteen DNP symbols remained after ADR 0009. They were not one thing:

| | | |
| --- | --- | --- |
| **8** | C26 C27 C28 C29 R53 R54 R62 R65 | the right mic channel |
| **4** | R48 R50 R64 R66 | divider legs whose *value* is `open` |
| **4** | R43 R44 R45 R46 | panel-io circuit options |

**The right channel carried the same defect ADR 0009 was written to fix, and
clearing its DNP would have shipped it.** The right channel is laid out as an
exact mirror of the *pre-jumper* left — 149.86 mm down the sheet, part for part.
That means it inherits both of the mutually exclusive pairs:

```
/audio/MIC_R      J18.2  C27.1  R65.1
                  R53.2 -> +3V3A   (2k2,  electret bias)
                  R54.2 -> +5V     (220R, carbon bias)

AUDIO_IN_R        A1.17  R66.1
                  C29.2 -> op-amp output
                  R65.2 -> raw MIC_R (bypass)
```

Fitting both bias resistors puts 2k2 to 3V3 against 220R to 5 V on the capsule.
Fitting both output paths shorts the op-amp output to the raw capsule signal.
**"Populate the right channel" and "the right channel works" are therefore not
the same instruction** — populating it without jumpers produces a board that is
wrong in exactly the way 0009 exists to prevent.

**An `open` position cannot be populated at all.** The other twelve are parts
awaiting a decision, and clearing `dnp` assembles them. R48, R50, R64 and R66
have the value `open`: the footprint exists precisely so that nothing is fitted.
No supplier ships an `open`. The rule leaves two moves — delete, or invent a
value — and inventing one buys four placements per board to satisfy a rule.

## Decision

**No symbol on any sheet carries `dnp`.** One exception is recorded and it is
not a DNP: **BT1 is `self_fit`** — populated on every board, bought from
Digi-Key and hand-soldered, stripped from `bom.csv`/`cpl.csv` into
`self-fit.csv`. That is an assembly routing decision, not a population one, and
`lcsc.yaml` already carries the distinction.

### The right channel is a full mirror, jumpers and all

**Three more jumpers, and one genuinely new part.**

| Jumper | Selects | Positions |
| --- | --- | --- |
| **JP4** bias | capsule supply | `3V3A` (R53, 2k2) · `OFF` · `5V` (R54, 220R) |
| **JP5** path | signal route | `AMP` (C29) · `BYPASS` (R65) |
| **JP6** gain | R62 leg | `x101` (R62, 1k) · `x256` (R68, 392R) |

**R68 is new, not a translation.** The left has two gain legs, R58 1k and R67
392R. The right had only R62 1k, because a follower needs no second leg. Without
R68 there is nothing for JP6 to select and the right channel cannot reach the
dynamic capsule's 60 dB.

**R59/R60/R61 change meaning without changing value.** ADR 0009 populated them
to stop section B floating — a unity-gain follower at `VBIAS_R` with R62 open.
They are now the mid-rail reference and feedback resistor of a working channel.
Same three parts, same values; what was a muzzle is now the circuit.

**The two channels are now symmetric**, which reverses 0009's "deliberately
asymmetric, recorded so it is not read as an oversight later". Both channels
take any of the three capsule types, so caryatid supports a stereo pair or two
different elements, and [mic-configurations.md](../mic-configurations.md)
describes one procedure rather than two.

### The four `open` legs are deleted

**R48/R50 — the line-out shunt.** The series arm survives and is the attenuator
[audio.md](../audio.md) actually argues for: 1 kΩ in series with a 150 Ω
earpiece is simultaneously the impedance fix (the output sees 1.15 kΩ instead of
150 Ω) and the ~13% attenuation a telephone receiver needs. The shunt was
flexibility, never function.

**R64/R66 — the carbon pad.** The WM8731's line PGA reaches **−34.5 dB**
(`PD Rev 4.0` Table 3, `LINVOL`/`RINVOL` at `00000`) — more attenuation than a
resistor pad would ever have been asked for, adjustable at run time rather than
fixed by a soldering iron. **That is ADR 0009's own argument applied to the
pad**: the codec already answers this question after assembly.

> **R66 was on the wrong node anyway, and nobody had noticed.** R64 taps
> `BYPASS_L`, ahead of JP2, so the pad stays in the bypass path where the carbon
> capsule needs it. R66 taps `AUDIO_IN_R`, which is *downstream* of where JP5
> lands — it would have padded the op-amp output too. Keeping the right pad
> would have meant moving it first. Deleting it removes a latent defect as well
> as a DNP.

### The four panel-io options are assembled

Both exclusions turned out not to survive the numbers.

**The pull-ups do not spoil a UART.** R43/R44, 4k7 to `+3V3` on D11/D12, were
DNP because "a UART on the same pins does not want them". A UART line **idles
high**, so the pull-up holds it where it already belongs; the cost is 0.7 mA
while a driver pulls it low, on a board that budgets tens of milliamps for
carbon mic bias alone. A floating RX is the worse of the two states.

**The pulldowns touch nothing else** — checked against the netlist rather than
assumed. J5, the analogue bus, carries A0–A3 and A6–A9. **A4 and A5 reach only
J10 and J9**, so R45 (3k, SoftPot) and R46 (10k, FSR) can affect no other input,
and on an instrument fitting neither sensor the pin reads a defined 0 instead of
floating.

Values are unchanged, and remain the corrected assignment from
[pinmap.md](../pinmap.md) — 10k on the FSR at A4, 3k on the SoftPot at A5.

## Consequences

**Good:**

- **The BOM becomes the board.** Every line is fitted; there is no second list
  and no instruction that has to reach the assembler in prose.
- **Both mic channels work out of the box**, selectable with a shunt.
- A latent wrong-node defect (R66) is gone.
- **The rule is checkable.** `check_board.py` check 12 fails on any `dnp` in any
  sheet, so this cannot quietly erode.

**Bad — real, not formalities:**

- **Every board pays for both mic channels** whether or not the instrument uses
  a mic at all — now ~24 audio parts plus U4 and six headers, where ADR 0009
  already accepted ~15 plus U4 and three.
- **Three more jumpers are three more things to mis-set.** The mitigation is
  0009's: the silkscreen carries the identification test beside the positions.
  It now has to do that twice, in the same board area.
- **The carbon pad is gone as a hardware option.** If a measured capsule ever
  overloads the input past what −34.5 dB of PGA can hold, the fix is a resistor
  in the loom, not on the board.
- **The `open` legs cannot come back without a board spin.** They were free
  optionality and they are being spent.
- **This delays fabrication a second time**, on a board that was verified and
  ready to order before ADR 0009.

**Neutral:**

- JP1–JP3's value strings gain an ` L` suffix. With six jumpers "Mic bias
  select" no longer says which channel. The BOM groups by LCSC part number, not
  value, so this splits no line.

## What this does not change

`MIC_RTN` still leaves via J18 pin 3 and pairs with J14 to the hook switch's
second pole, and it is **shared by both channels** — one gated return, two
capsules. A stereo carbon pair would draw both bias currents through it. That is
the correct arrangement (the gate is per-handset, not per-capsule) but it is
worth knowing before anyone sizes the switch.

BT1 remains self-fit, for the reasons in [status.md](../status.md): JLC quoted
21 days on the pre-order and Digi-Key is both cheaper and immediate.