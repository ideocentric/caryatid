# Bring-up runbook

**How to prove a fabricated caryatid board works, from the antistatic bag to a
Daisy Seed running `panel_readout`.**

Written 2026-09-02, for the first batch: five boards, JLCPCB order of
2026-08-23, ENIG, Economic assembly top side, arrived 2026-09-01.

Nothing in this repository has ever been powered. Every number below is
**predicted** from the schematic and the design documents, and none of it has
been seen on an instrument. That is the point of running it.

> **This runbook is a platform artifact, not a loa document.** Four more boards
> and every future batch use it. Keep instrument-specific steps out of it.

---

## Before you start

### The five rules

1. **Never power a rail you have not proved is not shorted.** Stage 1 exists
   entirely for this, and it is the stage with no glamour and the highest value.
2. **Every pass criterion is a number.** "Looks right" is not a result. If a
   step does not tell you what value to expect, it is not finished being
   written; say so rather than improvising a threshold at the bench.
3. **Record as you go, per board.** A runbook with no record is a runbook you
   run twice. See [Recording](#recording).
4. **Stop at the first red gate.** Do not press on to see whether the next
   thing also fails. On this board the failure modes are cumulative: a shorted
   rail that survives one stage destroys a part in the next.
5. **One board all the way before the other four.** You are proving the runbook
   as much as the hardware, and debugging five boards at once is debugging none.

### What you have, and what it costs you

You have **a multimeter and nothing else**. That is enough to complete this
runbook, and there are things it cannot reach. They are listed here so that a
gap is recorded as untested rather than quietly counted as passed.

| Cannot be checked without a scope | Consequence |
| --- | --- |
| Boost switching node and ripple | U2 could be running badly and still read 5.0 V DC |
| Inrush and start-up transient | A marginal soft-start shows only as an occasional failure to come up |
| RC debounce timing on the 74HC14 | ADR 0007's 24 ms figure stays unverified; firmware may need tuning |
| Audio noise floor and THD | You will know audio *works*, not how well |
| I2C and SPI signal integrity | Works or does not; no margin measurement |

| Cannot be checked without a current-limited supply | Mitigation used here |
| --- | --- |
| Safe first power-up into an unknown board | The series-resistor ladder in [Stage 2](#stage-2-first-power) |
| Precise quiescent current | Inferred from the drop across a known resistor |

**One purchase would change both columns**: a bench supply with an adjustable
current limit. It is not required to finish this runbook, and it is the single
most useful thing to own the next time a board arrives.

### Consumables and rigs you need

Confirm you have these **before** starting. Several are not on any BOM, because
they are test equipment rather than parts.

- [ ] **DC adapter for J1**, 5 to 9 V, centre-positive barrel.
      🔴 **Never 12 V.** The bq24074's input over-voltage protection trips at
      10.2 to 10.8 V. See [power-sheet.md](power-sheet.md).
- [ ] **Series resistors for the power ladder**: one 100 Ω and one 10 Ω, both
      **1 W or better**. A 100 Ω at 9 V dissipates 0.81 W into a dead short.
- [ ] **Test leads with clips.** Hand-held probes on a 0603 pad is how the loa
      hook switch produced 27 kΩ from a piece of metal. Clip everything.
- [ ] **Jumper wire** to bridge J3 for the boost enable, and to make temporary
      links at J14.
- [ ] **6 shunts per board** for JP1 to JP6 (Sullins SPC02SYAN, in hand).
- [ ] **BT1 holders and M3 screws.** Holders in hand; **screws are still
      unsourced**, see [`bt1-cell-fit`](../discovery/findings/bt1-cell-fit.yaml).
      Stage 4 is blocked until they arrive, and every earlier stage is not.
- [ ] **A protected 18650**, in hand.
- [ ] **A Daisy Seed**, in hand.
- [ ] 🔴 **Mating cables for the connectors.** This is the one likely to stop
      you. Full platform coverage means plugging into **JST-XH 2, 3, 4 and 6
      way, JST-SH 4 way, and IDC 2×5**. If these are not in hand, Stages 1
      through 7 still run in full and [Stage 8](#stage-8-functional-sweep)
      is where you stall. Check now, not on the day.

### Numbering the boards

Write **1 to 5** on each board in marker before you touch anything else, on the
bottom silkscreen where nothing will cover it. Every reading below is recorded
against that number. Boards that are physically indistinguishable become
indistinguishable results, and a batch fault then looks like a flaky board.

---

## Stage 0: Inventory and visual

**All five boards. No power. No meter.**

| # | Do | Pass |
| --- | --- | --- |
| 0.1 | Count the boards | 5 |
| 0.2 | Photograph both faces of each board, in focus, whole-board | 10 images filed under `discovery/evidence/` |
| 0.3 | Compare the populated set against `local/fab/bom.csv` and `cpl.csv` | 92 placed parts present |
| 0.4 | Confirm **BT1 is absent** | absent, it is `self_fit` |
| 0.5 | Confirm **JP1 to JP6 are bare headers**, no shunts fitted | bare |
| 0.6 | Look for solder bridges, tombstoned 0603s, missing parts | none |
| 0.7 | Check **U1 (QFN-16) and U2 (SOT-563) orientation** against the fab images | pin 1 as drawn |
| 0.8 | Check **C7 polarity**, the 100 µF electrolytic | band to the marked pin |
| 0.9 | Check **IDC pin-1 and JST polarity on J5 and J11** | as `sourcing.md` warns, these came from absonus and were flagged as worth re-checking rather than assuming |

**Gate:** any board failing 0.3 to 0.9 is set aside and recorded. Do not "fix"
anything yet; note it and finish the inventory first, because the same defect on
several boards is a batch fault and tells you something a single fix would hide.

---

## Stage 1: Dead-board electrical

**All five boards. No power. This is the stage that protects every later one.**

Meter in resistance. Probe at connector pins rather than at fine-pitch parts:
every rail reaches a connector, which is what [connectors.md](connectors.md) is
for. Do not restate pinouts from memory; read them from
[pinmap.md](pinmap.md), which is generated from the frozen
[`pins.yaml`](pins.yaml).

### 1a. Rail-to-ground shorts

For each rail, measure to GND. **Expect high resistance in at least one probe
polarity.** Semiconductor junctions make these readings polarity-dependent and
often non-linear, so a low reading one way round is not automatically a fault;
a low reading **both** ways round on a power rail is.

| Rail | Reach it at | Red flag |
| --- | --- | --- |
| `VIN_DC` | J1 | low both ways |
| `VBAT` | BT1 pads | low both ways |
| `VOUT` | J3, J4 | low both ways |
| `+5V` | J12 pin 1, J15, J16, J19 | low both ways |
| `+3V3` | J15, J16, J19 | low both ways |
| `+3V3A` | J5 outer pin, J9, J10 | low both ways |
| `+3V3D` | J11 | low both ways |

**Gate: any rail reading under ~10 Ω to ground in both polarities stops that
board.** Do not power it. Find the bridge first.

### 1b. Rail-to-rail isolation

Check that the rails are not shorted **to each other**, which a stray bridge
between adjacent connector pins produces and which 1a will not catch: `+5V` to
`+3V3`, `+3V3` to `+3V3A`, `+3V3A` to `+3V3D`, `VOUT` to `+5V`.

### 1c. Ground continuity

`AGND` and `DGND` should be continuous with the main ground pour and with each
other, near 0 Ω. They are one net on this board; if they read open, something is
wrong with the pour or with the probe.

### 1d. D1 orientation

Diode test across D1 (SS34, SMA). Forward roughly **0.2 to 0.4 V**, a Schottky,
lower than the 0.6 V of a silicon diode. Open the other way. Reversed, D1
blocks the input rather than protecting it, and the board simply never powers.

### 1e. Seed socket sanity

At A1 and A2, check adjacent pins are not bridged, and confirm the socket rows
are not shorted to each other. Twenty pins each, 100 SMT joints on the board:
this is where a bridge is most likely and most expensive.

**Gate: all five boards pass 1a to 1e before any board is powered.** Record each
board's result separately, because this is the stage that reveals a batch fault.

---

## Stage 2: First power

**Board 1 only. No cell. No Seed. No shunts.**

The board has never had voltage on it. With no current-limited supply, the
protection comes from a **series-resistor ladder**: start with enough resistance
that a dead short is harmless, and step down only once the current proves sane.

### The ladder

Wire the adapter to J1 **through a series resistor**, and measure the voltage
**across the resistor**. Current is that drop divided by the resistance. This
gives you both a limiter and an ammeter with the one instrument you have.

| Step | Series R | Worst case at 9 V | What to look for |
| --- | --- | --- | --- |
| 2.1 | **100 Ω** | 90 mA into a dead short | drop should be small: a healthy idle board is a few mA, so expect well under 1 V |
| 2.2 | **10 Ω** | 900 mA | drop of tens of mV; recompute the current and confirm it agrees with 2.1 |
| 2.3 | **direct** | unlimited | proceed only if 2.1 and 2.2 both gave a sane, stable current |

🔴 **A large drop at step 2.1 means the board is drawing heavily. Stop.** At
100 Ω the board is protected; that is the whole reason for starting there. Do
not "try it direct to see."

### What should happen

With the barrel in and **no cell fitted**, the bq24074 runs in supplement mode
and brings `VOUT` up from the input.

| # | Measure | Expect |
| --- | --- | --- |
| 2.4 | `VOUT`, at J3 or J4 | present and stable, below the input, in the region of 4.4 to 4.5 V |
| 2.5 | `/PGOOD` at J4 | asserted, meaning external power is present |
| 2.6 | `+5V` rail at J12 pin 1 | 🔴 **dead, and that is correct.** See below |
| 2.7 | Board temperature by hand | nothing warm. A warm QFN with no load is a fault |

### 2.6 is the step people fail

**The 5 V rail is supposed to be dead here.** The latching panel switch asserts
the boost's enable, and R6 is a 100 kΩ pulldown holding it off. With no switch
fitted, U2 never starts. A dead 5 V rail at this stage is the design working.

This is written as its own step because a dead rail looks exactly like a dead
boost, and the next stage is where you find out which.

**Gate:** `VOUT` present, `/PGOOD` asserted, `+5V` absent, nothing warm.

---

## Stage 3: The boost

**Board 1. Still no cell, still no Seed.**

| # | Do | Expect |
| --- | --- | --- |
| 3.1 | Jumper J3 to assert the boost enable. Pin roles are in [connectors.md](connectors.md): the switch closes `OUT` onto the EN return | |
| 3.2 | Measure `+5V` at J12 pin 1 | **4.954 V nominal**, acceptable **4.744 to 5.168 V** |
| 3.3 | Measure `+5V` at J15, J16, J19 | same value, within meter resolution |
| 3.4 | Measure across FB1 | a few tens of mV at most; a large drop means the bead is wrong or the load is high |
| 3.5 | Re-measure input current via the ladder | risen, but modest with no load |
| 3.6 | Feel U2 and L1 | warm is acceptable, hot is not |

The 4.744 to 5.168 V band is the divider tolerance from
[values.md](values.md), R7 348 kΩ and R8 47.5 kΩ against the TPS61023 feedback
reference. **A reading inside that band is a pass even if it is not 5.00 V.**
Reading 4.95 and "correcting" it is how a good board gets modified into a bad
one.

🔴 **Not verified at this stage, and it must be recorded as such:** ripple,
switching frequency and load transient response. The DC value being right does
not establish that U2 is switching cleanly. Mark it untested.

**Gate:** `+5V` inside the band, at every connector that carries it, nothing hot.

---

## Stage 4: BT1, the charger and the cell

**Blocked until the M3 screws arrive.** Everything before and after this stage
runs without them; only this one waits.

### 4a. Fit the holder

BT1 is `self_fit`: two through-hole joints, `VBAT` and `GND`, plus two M3 bolt
holes at 55.610 mm. **Fit it last of all the parts**, per `self-fit.csv`: it is
the tallest thing on the board and it spans 72.9 mm, so it obstructs everything
underneath it once fitted.

After soldering, **repeat Stage 1a for `VBAT`**. You have just added two joints
to a rail that a cell will shortly be asked to drive.

### 4b. The cell

| # | Do | Expect |
| --- | --- | --- |
| 4.1 | Measure the cell's open-circuit voltage before fitting | 3.0 to 4.2 V, and note it |
| 4.2 | Seat the cell, watching the orientation against the holder marking | seats without forcing |
| 4.3 | Measure `VBAT` at the holder | matches 4.1 |
| 4.4 | With the barrel **out**, check `VOUT` | alive, running from the cell |
| 4.5 | Jumper J3 and check `+5V` | inside the band, now boosted from the cell rather than from the barrel |

**4.5 is the real test of the instrument's power architecture**: it is the first
time the board has run on battery alone, which is how it will spend most of its
life.

### 4c. Charging

| # | Do | Expect |
| --- | --- | --- |
| 4.6 | Barrel in, cell fitted, partially discharged | `/CHG` asserts at J4 |
| 4.7 | Measure charge current into the cell | **0.90 to 1.10 A** |
| 4.8 | Watch `VBAT` over some minutes | rising |
| 4.9 | Measure total input current | under the **1.29 A** input limit |

The 0.90 to 1.10 A band is wide **and that is not slop in the resistor**. R3 is
887 Ω at 1%, but `KISET` spans 797 to 975 AΩ across the part's own tolerance, so
the spread is the bq24074's, not yours. See [values.md](values.md).

🔴 **Do not leave a charging cell unattended on a board being brought up for the
first time.** Everything about the charge path is unproven until this stage
completes.

**Gate:** charge current in band, `/CHG` correct, `VBAT` rising, nothing hot.

---

## Stage 5: The Seed, on its own

**Independent of the board. Do it whenever; it must be done before Stage 7.**

Your toolchain is not set up, so this stage separates two things that will
otherwise be confused: *a board fault* and *a toolchain fault*. Prove the Seed
works before it goes anywhere near the socket.

| # | Do | Pass |
| --- | --- | --- |
| 5.1 | Install the ARM toolchain and build libDaisy | libDaisy builds clean |
| 5.2 | Build and flash the stock libDaisy blink example over USB | LED blinks |
| 5.3 | Flash something that uses `StartLog` and prints | text arrives over USB serial |
| 5.4 | Build `firmware/examples/panel_readout.cpp` against libDaisy | **compiles**, not yet run |

**5.4 has never been done.** `firmware/README.md` says the code is a stub that
has never been on hardware. Expect to fix build errors here, and treat that as
expected work rather than as a discovery about the board.

**Gate:** a Seed you trust, and a binary that builds.

---

## Stage 6: The socket, Seed still out

**Board 1, powered, Seed NOT inserted. The last chance to catch a fault before
risking a Seed in it.**

Read the expected pin roles from [seed-sheet.md](seed-sheet.md); do not work
from memory or from a Seed pinout card.

| # | Measure at the socket | Expect |
| --- | --- | --- |
| 6.1 | The pin that feeds the Seed its input power | `+5V`, inside the band |
| 6.2 | Every ground pin | 0 Ω to ground |
| 6.3 | `3v3A`, socket pin 21 | 🔴 **absent, and that is correct.** See below |
| 6.4 | Any other pin, against ground | no rail where a GPIO belongs |

### 6.3 is the counterpart of 2.6

**`+3V3A` originates at the Seed, not on the board.** It leaves the Seed on pin
21 and feeds the J5 pot tops, J9 and J10. With the Seed out, `+3V3A` is dead and
so is `+3V3`. If you measure 3V3 anywhere with the Seed out, something is
feeding it that should not be, and that is a fault worth chasing before you
insert a Seed into it.

**Gate:** 5 V present where 5 V belongs, no voltage where none belongs.

---

## Stage 7: Seed in the board

| # | Do | Expect |
| --- | --- | --- |
| 7.1 | Power down completely. Insert the Seed, watching orientation | seats fully |
| 7.2 | Power up through the **10 Ω** series resistor, not direct | current rises to a sane figure |
| 7.3 | Measure `+3V3` and `+3V3A` | both now present |
| 7.4 | Flash `panel_readout` | runs |
| 7.5 | Open USB serial | readings once per second |

**Gate:** the board talks. Everything after this is coverage rather than
survival.

---

## Stage 8: Functional sweep

**Full platform coverage: every connector and every subsystem, including the
ones loa will never use.** A fault in an unused corner is still a fault, and
absonus or baby borg will find it later at much greater cost.

Needs mating cables. See the consumables list.

### 8a. Analogue bus, J5

`A0`–`A3` then `A6`–`A9`, **not** `A0..A7`. `A4` and `A5` are not on the bus.
Each wiper has 1 kΩ/100 nF board-side.

Feed each channel a known voltage, ideally 0 V, half rail and full rail, and
confirm `panel_readout` reports it. **Sweep them one at a time and confirm only
the expected channel moves**, which is what catches a swapped pair. A pot per
channel is convenient; a resistor divider on a jumper wire is sufficient.

### 8b. Dedicated analogue, J9 and J10

`A5` soft pot with a 3 kΩ pulldown, `A4` FSR with a 10 kΩ pulldown. **With
nothing plugged in, both should read a defined low value rather than floating.**
That is what the pulldowns are for, and an open reading means one is missing.

### 8c. Battery gauge, A10

Compare the reported value against `VBAT` measured at the holder.
**Expect the pin to read half the cell voltage**, the 100 k/100 k divider, and
the firmware to report the doubled figure. A factor-of-two error here is the
easiest bug on the board to write and the hardest to notice.

### 8d. Charge status, A11

Four levels, and you can produce three of them. From
[indicators.md](indicators.md):

| `/CHG` | `/PGOOD` | State | Level |
| --- | --- | --- | --- |
| high-Z | high-Z | idle, on battery | **3.300 V** |
| high-Z | low | external power, not charging | **2.200 V** |
| low | high-Z | charging | **1.650 V** |
| low | low | charging, external present | **1.320 V** |

Produce them by pulling the barrel in and out with the cell at different states
of charge. **Decode by nearest level, not by thresholds.** Minimum separation is
330 mV, which is 409 ADC counts against noise of a few.

### 8e. Digital bus, J11

`D0`–`D6`, 100 Ω series each. Ground each line in turn and confirm the expected
bit changes and **only** that bit. This is the bus loa's keypad uses, and
[`loa-keypad-matrix`](../discovery/findings/loa-keypad-matrix.yaml) is confirmed,
so a real keypad is available as a test article if you want one.

### 8f. Switches, J6 J7 J8

🔴 **Two traps, both documented and both easy to trip.**

- **They read inverted.** The 74HC14 is an inverter, so the GPIO is **high when
  the switch is closed**. A switch that reads "backwards" is correct.
- **SW1 and SW2 cross.** SW1 is on `D14`, SW2 is on `D13`. Not a typo.

Short each of J6, J7 and J8 in turn and confirm the right bit moves.

🔴 Debounce timing is **not verified** by this and cannot be with a meter.
ADR 0007's 24 ms for a 1 µF hook lever stays a calculation.

### 8g. RGB status, J12

**Common anode to 5 V, GPIOs sinking. Writing low lights it.** Pin 1 is `+5V`,
not ground and not 3V3.

Drive each channel low in turn: red through 510 Ω, green and blue through 300 Ω.
**Green and blue will not light from a 3V3 GPIO driven high**; their forward
voltage is above the output-high level. That is why the scheme sinks.

Check all three individually, then together for white.

### 8h. Audio, J17 and J18

Both channels are fitted on every board and jumper-selected.

- **Out, J17:** generate a tone in firmware, confirm L and R independently at the
  connector. Confirm they are not swapped and not summed.
- **In, J18:** feed a known signal, confirm it arrives on the right channel.
  Remember pin 3 is **`MIC_RTN`, not ground.**

### 8i. Mic configurations, JP1 to JP6

Six shunts, and exactly one bias path connected at a time. Work through
[mic-configurations.md](mic-configurations.md) and confirm each selection does
what that document says.

For an **electret**, JP1 and JP4 on `1-2` gives bias through R51/R53 at 2k2,
**1.5 mA per channel** per [values.md](values.md).

### 8j. Comms A, J13 and J19

Port A is protocol-agnostic per ADR 0003. Test it as I2C with a Qwiic or
STEMMA-QT device on J13, and as UART on J19. **These are alternates: pick one
per port and it must match what firmware is configured for**, which
`panel_readout` sets in `cfg.comms_a`.

### 8k. Comms B, J15

`D13` and `D14`. 🔴 **These are the same pins as SW1 and SW2.** J6/J7 and J15 are
mutually exclusive, which is why the hook switch is on SW3. Testing this means
disconnecting the switches.

### 8l. Expansion, J16

SPI1 on `D8` SCLK, `D9` MISO, `D10` MOSI, `D30` CS, plus 5 V, 3V3 and two
grounds. `D30` is the only spare pin on the board and it is brought out here.

---

## Stage 9: The other four boards

Once board 1 is through Stage 8 and the runbook has been corrected by
contact with reality:

1. Stage 1 is already done on all five.
2. Take each remaining board through **Stages 2, 3, 6 and 7**: power, boost,
   socket, boot. That proves it is alive.
3. Run **Stage 8 only on the subsystems each board will actually use**, unless a
   board is destined to be a spare, in which case Stage 7 is a reasonable stop.

**Fix the runbook before running it four more times.** Anything that was wrong,
ambiguous or missing on board 1 gets corrected here, not remembered.

---

## Recording

**One findings record per board**, `discovery/findings/board-<n>.yaml`, using
the schema in the global methodology plus a `stages` block. Status is
`in-progress` while the board is partway through, and only `confirmed` once
every stage attempted has passed.

Evidence goes to `discovery/evidence/` with dated filenames, including the
Stage 0 photographs.

Three things to record that are easy to skip:

- **The actual numbers, not "pass".** 4.98 V is a fact; "5 V rail OK" is not.
  The band is wide and the middle of it tells you more than the edges.
- **What was NOT tested**, explicitly. Ripple, switching, debounce timing and
  audio quality are all out of reach with a multimeter, and a record that omits
  them reads as though they passed.
- **Anything the runbook got wrong.** This document has never been run. Its
  first pass is as much a test of itself as of the board.
