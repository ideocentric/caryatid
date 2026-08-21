# Connectors

Every variable element enters through a connector. The PCB layout is identical
for every instrument; each build populates a subset. Order once, stuff per
instrument.

Pin assignments are in [pinmap.md](pinmap.md), generated from
[pins.yaml](pins.yaml). This file covers the connectors themselves.

| Ref | Type | Carries |
| --- | --- | --- |
| J1 | JST-XH 2 | 5–9 V in, **from a panel-mounted barrel jack**. Never 12 V. |
| BT1 | MPD BH-18650-PC, on-board | **The cell.** Rated for *protected* cells (~69 mm) — stated on the drawing. `C5339083`. |
| J3 | JST 4 | Latch switch: OUT→sw, EN return, 5 V→lamp, GND |
| J4 | JST 4 | `/CHG` and `/PGOOD` panel LEDs, 1k each from OUT |
| J5 | IDC 2×5 | **Analogue bus** — A0–A3, A6–A9 + 3V3A + AGND. Rails on the outer pins; **1kΩ/100nF** per wiper, board side — see [values.md](values.md). |
| J6 | JST 2 | SW1 → D14 via 74HC14 — *or* J15 takes the pins |
| J7 | JST 2 | SW2 → D13 via 74HC14 — *or* J15 takes the pins |
| J8 | JST 2 | SW3 → D7 via 74HC14 |
| J9 | JST 3 | Soft pot: 3V3A, A5, AGND |
| J10 | JST 2/3 | FSR: 3V3A, A4 |
| J11 | IDC 2×5 | **Digital bus** — D0–D6 + 3V3D + DGND + spare. 100Ω series each. |
| J12 | JST 4 | RGB status. **Common anode**: pin 1 `+5V`, then D26/D27/D29 cathodes sinking through **510Ω red, 300Ω green, 300Ω blue**. Not GND, not 3V3 — see [panel-io-sheet.md](panel-io-sheet.md). |
| J13 | JST-SH 4 | **Comms port A** as I2C — Qwiic / STEMMA-QT pinout |
| J14 | JST-XH 2 | Mic bias return → the hook switch's second pole |
| J19 | JST-XH 6 | **Comms port A** as a module port — 5V, 3V3, GND, D11, D12, GND |
| J15 | JST-XH 6 | **Comms port B** — 5V, 3V3, GND, D13, D14, GND |
| J16 | header 2×4 | **Expansion / SPI1** — 5V, 3V3, GND, GND, D8 SCLK, D9 MISO, D10 MOSI, D30 CS |
| J17 | JST-XH 3 | Audio out — L, R, GND, to panel jacks |
| J18 | JST-XH 3 | Audio in — L, R, **`MIC_RTN`**. Both channels fitted and jumper-selected on every board |

> **Three entries in that table were wrong until the silkscreen work checked
> them against the schematic.** They are recorded here because the error was in
> this file, not on the board, and the next person to read it should know it has
> been reconciled rather than merely written:
>
> - **J19 and J15 pin 6 were listed as `AUX`. Both are `GND`.** There is no
>   `AUX` net anywhere in the schematic or the board — the name existed only
>   here. Each port carries **two grounds**, which is what a six-way cable to a
>   module wants anyway.
> - **J19 and J15 were listed as JST-PH. Both are JST-XH**, `B6B-XH-A` at
>   2.50 mm, per the schematic's own Footprint property. Ordering PH housings
>   against this table would have produced parts that do not mate.
> - **J18 pin 3 was listed as `GND`. It is `MIC_RTN`** — the mic bias return,
>   which pairs with J14 pin 1 and is precisely *not* a ground; that is the whole
>   point of J14.
>
> Nothing on the board changed. The schematic and the PCB agreed with each other
> throughout; only this file disagreed with both.

## Every pin reaches a connector

There are no stranded pins. `A10` and `A11` are on-board by definition — they
measure the board's own battery and charger — and every other pin lands on
something you can plug into.

That includes the spare. **`D30` is brought out on J16**, so "spare" means
usable rather than merely unallocated. J16 is a 2×4 rather than the 2×3 the
signals strictly need: the extra two positions carry **5 V and a second ground**,
which cost no Seed pins and are what a display or an SD card will want. A spare
pin on a header you can reach is worth something; a spare pin on a pad is worth
nothing.

## Silkscreen every connector's pinout

This board is assembled once and **cabled differently for each instrument**, by
hand, months apart. The loom is where the mistakes will be, not the PCB.

So **print the function of every pin beside every connector** — `+3V3A`, `A5`,
`GND` at J9; `VOUT`, `CHG`, `PGOOD`, `GND` at J4 — and mark pin 1 on all of them.
It costs nothing at fabrication and it is the difference between crimping a loom
from the board and crimping it from a document that may not be open.

Same argument as printing the pin names beside the Seed sockets. The board should
be readable without its documentation.

## Nothing mounts on the board edge

Every panel part is panel-mounted and reaches the board by wire: the DC jack
(DC-099, threaded), the 3.5 mm audio jacks, the LED bezel and the latching
switch. So **the board carries no jack footprints at all** — J1, J17 and J18 are
JSTs, and the jacks live wherever the enclosure wants them.

This is the right way round for a platform. Board-mounted jacks make the PCB
edge *be* the panel, which suits a sandwich enclosure and rules out a telephone
shell. Wire lets one board sit inside three different objects.

The cost is real and worth stating: **audio now travels on flying leads**, past
a 1 MHz boost converter, inside a shell. Keep J17 and J18 physically near the
audio section and far from the switcher, run the pairs twisted with their
grounds, and treat routing them as a layout constraint rather than something to
tidy up at assembly.

It also moves the single-point ground bond. Layout rule 5 said "at or near the
audio jacks" on the assumption they were on the board; with panel jacks, the
bond belongs at the panel end of the audio loom.

## Comms ports

The most useful thing in this design and the least obvious. **D11/D12 are
simultaneously I2C1 and UART4**, so a port is two signal lines whose protocol is
decided by what you plug in and a line of firmware config — not by the board.

| | Port A (D11/D12) | Port B (D13/D14) |
| --- | --- | --- |
| Protocols | I2C1, UART4 | USART1 |
| Typical use | I2C sensor, or MIDI | MIDI, or an ESP32 OSC bridge |
| Competes with | — | SW1 and SW2 |

**Two footprints on port A, populate one.** The 4-pin JST-SH follows
Qwiic/STEMMA-QT so an off-the-shelf sensor is a cable rather than a breakout you
design. The 6-pin JST-PH carries both rails plus an AUX line, which is what a
MIDI input opto or a radio module wants. Footprints are free; connectors are the
cost.

**Port B competes with SW1/SW2.** That is why loa's hook switch belongs on
**SW3 (D7)** — USART1 needs both D13 and D14, and a hook switch sitting on one
of them would quietly cost you the port.

**MIDI's opto-isolator lives on the daughterboard**, not here. The port carries
logic-level signals and power; isolation is the breakout's job. That keeps the
platform free of a circuit most builds do not populate.

## What the outside world sees is not a board decision

The board terminates audio at jacks and MIDI at a comms port. Whether the
instrument's panel presents three sockets or a single RJ45 carrying everything
is a panel-and-loom question, and it can be settled after the PCB.

For the record, if one cord is wanted for a single-direction MIDI input plus
stereo audio, six conductors do it and the split pair earns its keep as a guard:

| RJ45 pin | Pair | Signal |
| --- | --- | --- |
| 1, 2 | 2 | Audio L — signal + its own return |
| **3** | **3** | **GND guard** |
| 4, 5 | 1 | Audio R — signal + its own return |
| **6** | **3** | **GND guard** |
| 7, 8 | 4 | MIDI IN — to the opto LED |

Pair 3 is split across the connector in T568B, which makes it the worst pair for
signal and the best one for a guard: pin 6 sits physically between the audio and
the MIDI pair, exactly where the termination untwist makes coupling worst.

Two hazards if you go this way. **PoE** — an RJ45 on a panel invites a network
cable, and a PoE port will put 48 V into your line outputs. Use a locking shell
or a legend. And **RJ12 is the authentic phone connector but standard line cord
is flat untwisted ribbon**, so all the twisted-pair reasoning above evaporates;
it needs round shielded 6-conductor cable, which rather undercuts the point.