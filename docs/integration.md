# Integrating caryatid

**How to build an instrument on this board: what it gives you, what you must
provide, and what you may not change.**

This is the document to read first. [connectors.md](connectors.md) is the pin-by-pin
reference; this is the shape of the thing.

---

## What caryatid is

A common power and I/O carrier for a **Daisy Seed**. It provides the charger,
the boost converter, the indicators, the Seed socket, the audio jacks and every
panel connector. One PCB layout serves absonus, loa and baby borg — each
populates the subset it needs.

**150 × 90 mm, 2 layers, 92 placed parts** (32 more are laid out DNP).

| caryatid provides | the instrument provides |
| --- | --- |
| Battery charging, power path, 5 V boost | The panel, and whatever plugs into it |
| The Daisy Seed socket and its decoupling | The Daisy Seed itself |
| 18 connectors: analogue, digital, comms, audio, power | Cables, pots, switches, sensors |
| Charge and power indication that works with the Seed **off** | Firmware |
| RGB status LED, battery gauge, charge-status decode | The enclosure |

---

## The one rule: the pin map is frozen

[`docs/pins.yaml`](pins.yaml) is the source of truth. An instrument **may**:

- leave any pin unpopulated
- choose between the alternates a pin lists (I2C *or* UART on comms port A)

An instrument **may not repurpose a pin**. The entire value of the platform is
that one layout serves every build; a pin reassigned for one instrument is a
board that no longer serves the others.

The map is **fully allocated**. `D30` is the only spare, and it is brought out
to J16 rather than left floating — so "spare" means usable, not merely
unassigned. Adding anything means taking it from something else.

---

## Electrical requirements

### Power in

| | |
| --- | --- |
| Barrel jack via J1 | **5–9 V. Never 12 V.** |
| Cell | One **18650**, in the on-board holder BT1 |

**The cell must be protected** — either a protected cell or a pack with a
protection PCB. BT1 is the *only* path to `VBAT`; there is no second connector,
so a cell cannot be presented to the charger backwards.

The barrel input goes to 9 V, and the charger's `EN`/`CE` pins are 7 V absolute
maximum. That constraint is already handled on the board, but it is the reason
`EN2` ties to `VOUT` and not to the raw input — do not "fix" that if you fork
the schematic.

### What you get out

| Rail | Where | Notes |
| --- | --- | --- |
| **5 V** | Seed VIN, switch lamp, RGB anode | From the TPS61023 boost, via a ferrite and 100 µF |
| **3V3** | J11 pin 1, panel digital | Regulated by the Seed |
| **3V3A** | J5 pin 1, panel analogue | Separate supply, not a separate return |
| `VOUT` | charge LEDs | Live whether or not the boost is on |

**There is one ground plane.** `AGND` ties to `GND`; there is no split. Do not
introduce one at the panel.

### The 5 V budget is real and it is documented

See the line-item table in [values.md](values.md). The largest unresolved term
is mic bias — R52/R54 at 220 Ω each, so 23–41 mA for the pair depending on the
capsule, up to 16% of the typical rail load. If your instrument adds current on
the 5 V rail, check it against that table rather than assuming headroom.

---

## Mechanical requirements

| | |
| --- | --- |
| Board | 150 × 90 mm, 3 mm corner radius |
| Mounting | Four M3, **±70 × ±40 mm** about the board centre, 5 mm in from every edge |
| Standoff | **4 mm as built** (2 mm is the electrical minimum — everything is on the front face, so the back is bare copper) |
| Tallest part | 26.91 mm stack |

### If you use the BUD CU-477

Measured in hand, not derived — see
[the enclosure record](../discovery/findings/bud-cu477-interior.yaml):

- Interior floor **178 × 110 mm**, height **34.0 mm** (7.09 mm headroom)
- Corner screw columns inset **5 mm**

**The board is not centred.** It mounts **5 mm from the left wall**, hard
against the screw columns, putting all 28 mm of long-axis slack at the right
end. Two reasons, and they agree: the 12 mm latching power switch descends
**23 mm** and needs that space with no board under it, and the device is held
in the **left hand**, so the board's mass belongs over the supporting hand
rather than cantilevered right.

**Drill the floor from the walls, not from the centre:** 10 mm from the left
wall, 28 mm from the right, 15 mm from each long wall. Centring the pattern
puts the board 9 mm into the switch's space *and* throws the balance.

---

## Choices each instrument makes

The board lays out both options and a build fits one. **Firmware config must
match what is soldered** — selecting the wrong mode configures a peripheral onto
pins that are not connected, and it fails silently.

| Pins | Option A | Option B |
| --- | --- | --- |
| `D11`/`D12` | **I2C sensor** — J13a, 4-pin JST-SH, Qwiic/STEMMA-QT | **MIDI or UART bridge** — J13b, 6-pin JST-PH |
| `D13`/`D14` | **Comms port B** — J15, USART1 | **SW1 + SW2** via the 74HC14 — J6, J7 |

**Comms ports carry signals, not protocols.** `D11`/`D12` are simultaneously
I2C1 and UART4, so the same connector is an I2C sensor, a MIDI input, or an
ESP32 bridge depending on what you plug in. Two ports is the ceiling — there is
no third UART on free pins.

Also per-instrument:

- **The audio input network** is laid out on every board, DNP where unused. U4
  (MCP6002) sits DNP with a bypass so the **capsule question can be answered
  after the boards arrive** rather than before the Gerbers go out. Measure the
  capsule's DC resistance to decide between a preamp and a pad — see
  [audio.md](audio.md).
- **The switch debounce capacitor** is a per-channel population choice: 220 nF
  for a panel switch, 1 µF for a telephone hook lever.
- **`A4`/`A5` pulldowns** — 10 kΩ on the FSR, 3 kΩ on the soft pot. Do not
  transpose these; the platform spec did, and the fabricated absonus board is
  the authority.

---

## Firmware

Board support lives in [`firmware/`](../firmware/) and is **MIT licensed** so
instrument firmware can link it without inheriting copyleft.

```sh
git submodule add https://github.com/ideocentric/caryatid.git hardware/platform
```

```make
C_INCLUDES  += -Ihardware/platform/firmware/include
CPP_SOURCES += hardware/platform/firmware/src/caryatid.cpp
```

```cpp
caryatid::Config cfg;
cfg.comms_a = caryatid::CommsA::I2C;
hw.Init(seed, cfg);
while (1) { hw.Update(); System::Delay(1); }
```

Flash [`examples/panel_readout.cpp`](../firmware/examples/panel_readout.cpp)
first on a new board. It exercises every subsystem and prints the result, so a
mis-soldered connector shows up as a wrong number rather than as a silent
failure three weeks later.

### Four things that are not guessable from a pin number

The class handles all four, but you will meet them if you go around it:

1. **The RGB is common anode to 5 V** and the GPIOs sink — **low means lit**.
   Green and blue cannot be driven from a 3V3 GPIO at all; their forward
   voltage is above the output-high level.
2. **The switches invert.** They pass through a 74HC14, so the GPIO reads
   **high when pressed**. And **SW1 is on `D14`, SW2 on `D13`** — they cross.
3. **The battery gauge is halved** by a 100k/100k divider. Cell volts are 2× the
   pin. It draws ~21 µA continuously whether firmware reads it or not.
4. **J5 is `A0`–`A3` then `A6`–`A9`**, not `A0..A7`. `A4` and `A5` are dedicated
   sensor inputs on J10 and J9, not part of the bus.

### Charge state without a second pin

`/CHG` and `/PGOOD` are encoded as four voltage levels on `A11`, because the pin
budget had no room for two digital inputs:

| `/CHG` | `/PGOOD` | State | Level |
| --- | --- | --- | --- |
| high-Z | high-Z | idle, on battery | 3.300 V |
| high-Z | low | external power, not charging | 2.200 V |
| low | high-Z | charging | 1.650 V |
| low | low | charging, external present | 1.320 V |

Minimum separation 330 mV. `Caryatid::ChargeState()` decodes it. A reading
outside every band returns `Unknown` — that means a shorted pin or an
unpopulated network, not a fifth state.

**A battery reading near zero while the board is clearly powered** means the
cell is disconnected or its protection has tripped. Worth catching before a gig
rather than during one.

---

## Licensing

| | |
| --- | --- |
| Hardware — schematic, PCB, footprints, artwork | **CERN-OHL-S-2.0** |
| `firmware/` | **MIT** |
| `tools/` | **GPL-3.0-or-later** |

CERN-OHL-S defines *Complete Source* as the editable design files, so **shipping
Gerbers alone does not discharge it**. If you build on this board and distribute
the result, publish the KiCad project.

`firmware/` is deliberately permissive: a copyleft board-support layer would
force every instrument's firmware to match, and libDaisy and DaisySP are both
MIT already.

Full terms in [LICENSING.md](../LICENSING.md).