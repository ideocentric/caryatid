# Panel I/O sheet

Every connection on `hardware/pcb/panel-io.kicad_sch`: the two ribbon buses, the
switch debouncer, the comms ports, the RGB, the expansion header and the two
sensor inputs.

This is the sheet where the frozen map earns its keep. Nothing here is a design
decision — it is a wiring list, and the checkable property is that every net
name matches [pinmap.md](pinmap.md).

## Symbols

**All stock KiCad.** `74xx:74HC14`, `Connector_Generic:Conn_02x05_Odd_Even`,
`Connector:Conn_01x0N`, `Device:R`, `Device:C`, `Device:LED_ARGB`. No custom
symbol is needed on this sheet.

## One trap

**The sensor pulldowns were transposed in the platform spec** and are now
corrected: **A4 (FSR) takes 10 kΩ, A5 (soft pot) takes 3 kΩ.** The spec had them
the other way round, inherited from a stale ribbon-synth document that its own
schematic contradicts. The fabricated absonus board is the authority: R1 = 10 kΩ
on the pressure input, R2 = 3 kΩ on the position input.

## J5 — analogue bus, IDC 2×5

Rails on the outer pins, eight wipers between.

| Pin | Net |
| --- | --- |
| 1 | `+3V3A` |
| 2–5 | `A0`, `A1`, `A2`, `A3` |
| 6–9 | `A6`, `A7`, `A8`, `A9` |
| 10 | `GND` |

**Each wiper gets 1 kΩ in series and 100 nF to ground, board side.** Not
220 Ω / 10 nF — a 10 kΩ pot at mid-travel contributes 2.5 kΩ of source impedance,
which puts that network's corner at 5.9 kHz, well above the 1 kHz control rate
and squarely in the band that aliases. 1 kΩ / 100 nF lands it at 455 Hz. See
[values.md](values.md).

`A4` and `A5` are **not** on this bus — they are the dedicated sensor inputs
below.

## J11 — digital bus, IDC 2×5

| Pin | Net |
| --- | --- |
| 1 | `+3V3` |
| 2–8 | `D0` … `D6` |
| 9 | spare |
| 10 | `GND` |

**100 Ω in series on each of D0–D6**, board side. These are keypad scan lines on
loa; the series resistance limits current if two drivers ever contend and takes
the edge off the scan transitions.

## Switches — RC into a 74HC14

**U3 = 74HC14**, hex Schmitt-trigger inverter, SOIC-14, C5605. Replaces the
LS18-P the platform spec called for; the reasoning is in
[ADR 0007](decisions/0007-rc-and-schmitt-instead-of-the-ls18-p.md).

Per channel:

```
   +3V3 ──[ 10k ]──┬──[ 10k ]──┬── 74HC14 in
                   │           │
   J6.1 ───────────┘         [ C ]
                               │
   J6.2 ── GND                GND
```

| Channel | Connector | 74HC14 in | 74HC14 out | Net |
| --- | --- | --- | --- | --- |
| SW1 | J6 | 1 | 2 | `D14` |
| SW2 | J7 | 3 | 4 | `D13` |
| SW3 | J8 | 5 | 6 | `D7` |

Pin 14 `VCC` → `+3V3`, pin 7 `GND` → `GND`, plus **100 nF decoupling**.

**Tie the three unused inputs (9, 11, 13) to `GND`.** A floating CMOS input
oscillates and draws supply current; it is the classic way an unused gate
becomes a fault.

**loa's hook switch is SW3, on J8, reaching `D7`.** Not SW1 or SW2 — those are
`D13`/`D14`, which are comms port B, and USART1 needs both.

### The output is inverted, and that is the right way round

Switch closed reads high, switch open reads low. More usefully:

| | Input | Output |
| --- | --- | --- |
| Cable unplugged | pulled high | **LOW** |
| Switch open — on-hook | high | **LOW** |
| Switch closed — off-hook | low | HIGH |

**A disconnected cable reads identically to on-hook**, so the instrument stays
silent and the mic bias stays off. Restoring the polarity with a second inverter
would spend three of the spare gates to buy the opposite failure — a broken
lead reading as off-hook, audio live. Invert in firmware instead; it is free.

### Sizing C per channel

The resistors are fixed; the capacitor is a population choice, because a
telephone hook lever and a panel toggle do not bounce alike.

| C | Press | Release | For |
| --- | --- | --- | --- |
| 100 nF | 1.2 ms | 2.4 ms | marginal — below typical bounce |
| **220 nF** | **2.7 ms** | **5.3 ms** | panel switches |
| **1 µF** | **12 ms** | **24 ms** | **a hook lever** |

Release is twice press because the charge path runs through both resistors while
the discharge path runs through one. Small switches bounce 1–5 ms, big levers
5–20 ms, so 100 nF is not enough for a hook switch and 1 µF's 24 ms of latency is
irrelevant to one.

Each closed switch draws **330 µA** through its pull-up. Three at once is 1 mA,
negligible against a 250 mA instrument but not zero — worth knowing for a build
with latching switches that sit closed.

## J12 — RGB status

Common anode. **Anode on `+5V`**, cathodes sinking into the GPIOs.

| Pin | Net |
| --- | --- |
| 1 | `+5V` |
| 2 | red cathode → **510 Ω** → `D26` |
| 3 | green cathode → **300 Ω** → `D27` |
| 4 | blue cathode → **300 Ω** → `D29` |

Three different values, because red's forward voltage is a volt below the others.
Green's will likely rise toward a kilohm on tuning, since equal current is not
equal brightness. See [sourcing.md](sourcing.md).

## Comms port A — D11 / D12

Two footprints on the same two pins; populate one.

**J13 — JST-SH 4, Qwiic/STEMMA-QT pinout:**

| Pin | Net |
| --- | --- |
| 1 | `GND` |
| 2 | `+3V3` |
| 3 | `D12` (SDA) |
| 4 | `D11` (SCL) |

Plus **4.7 kΩ pull-ups to `+3V3` on both, fitted** (R43, R44). They were DNP —
"a UART on the same pins does not want them" — until
[ADR 0010](decisions/0010-nothing-is-dnp.md) checked that claim: **a UART line
idles high**, so a pull-up holds it where it already belongs and costs 0.7 mA
only while a driver pulls it low. A floating RX is the worse of the two states.

**J19 — JST-XH 6, module port:**

| Pin | Net |
| --- | --- |
| 1 | `+5V` |
| 2 | `+3V3` |
| 3 | `GND` |
| 4 | `D11` |
| 5 | `D12` |
| 6 | `GND` |

Pin 6 is a second ground rather than a spare signal — there is no spare Seed pin
to give it, and a return beside the signals is worth more than a floating pad.

## Comms port B — J15, D13 / D14

Same 6-pin pinout as J19, with `D13` and `D14` on pins 4 and 5.

**J15 and J6/J7 are mutually exclusive.** Populating port B means giving up SW1
and SW2, which is why the hook switch is on SW3.

## J16 — expansion, 2×4 header

| Pin | Net | | Pin | Net |
| --- | --- | --- | --- | --- |
| 1 | `+5V` | | 2 | `+3V3` |
| 3 | `GND` | | 4 | `GND` |
| 5 | `D8` — SCLK | | 6 | `D9` — MISO |
| 7 | `D10` — MOSI | | 8 | `D30` — CS |

`D8` is the only free SPI1 clock on the board. If anything else ends up on it,
stop and read [ADR 0004](decisions/0004-keep-spi1-drop-the-soft-latch.md).

## J9 — soft pot, JST-XH 3

| Pin | Net |
| --- | --- |
| 1 | `+3V3A` |
| 2 | `A5` |
| 3 | `GND` |

**3 kΩ pulldown from `A5` to `GND`, fitted** (R45; a DNP option until
[ADR 0010](decisions/0010-nothing-is-dnp.md)). A SoftPot wiper floats when
untouched; the pulldown gives it a defined reading instead of a drifting one.
**`A5` reaches only this connector** — the analogue bus J5 carries A0–A3 and
A6–A9 — so on a board with no SoftPot it simply reads a defined 0.

## J10 — FSR, JST-XH 2

| Pin | Net |
| --- | --- |
| 1 | `+3V3A` |
| 2 | `A4` |

**10 kΩ pulldown from `A4` to `GND`, fitted** (R46; a DNP option until
[ADR 0010](decisions/0010-nothing-is-dnp.md)). This is the transposition
corrected above. It is also worth knowing that the value sets the shape of the
force response, not just its presence — loa's pad work found the ribbon synth's
narrow usable range was largely the divider rather than the sensor.

## Population

Nothing on this sheet is populated on every build. The whole point is that a
board is stuffed for its instrument.

| Block | absonus | loa (phone) | baby borg |
| --- | --- | --- | --- |
| J5 analogue bus | 8 pots | 3–4 pots | TBD |
| J11 digital bus | — | 4×3 keypad | TBD |
| J6/J7/J8 switches | SW1, SW2 | **SW3 = hook** | TBD |
| J9 / J10 sensors | both | — | TBD |
| J12 RGB | ✓ | ✓ | ✓ |
| J13 Qwiic | — | — | ✓ distance sensor |
| J19 / J15 module | — | MIDI, if wanted | — |
| J16 expansion | — | — | — |

**The connectors above are fitted on every board regardless** — see
[sourcing.md](sourcing.md). The population table describes which ones get a
*cable*, not which ones get soldered.

**And since [ADR 0010](decisions/0010-nothing-is-dnp.md) the circuit options are
fitted too.** The I2C pull-ups and both sensor pulldowns were the last DNP on
this sheet; nothing here is unpopulated now. The table above is entirely about
looms.