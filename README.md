# caryatid

A common power and I/O board for Daisy Seed instruments — absonus, loa, baby
borg, and whatever comes next.

*A caryatid is a column carved as a figure, bearing the weight of what stands on
it. Named for the role rather than for any instrument it carries: calling it
after one of them would have implied it belonged to that one.*

**One PCB layout serves every build.** Every variable element — pots, keypad,
sensors, switches, comms — enters through a connector, and each instrument
populates the subset it needs. Order once, stuff per instrument.

Status: **schematic captured, board placed and fully routed.** Every electrical
check is at zero — no unconnected nets, no shorts, no clearance or hole
violations, no copper under the width rule, no floating ground. See
[docs/status.md](docs/status.md) for what is left and what happens next.

## Start here

| | |
| --- | --- |
| **Where the board is, and what is next** | [docs/status.md](docs/status.md) |
| **The frozen pin map** | [docs/pinmap.md](docs/pinmap.md) — generated from [docs/pins.yaml](docs/pins.yaml) |
| Connectors and what plugs into them | [docs/connectors.md](docs/connectors.md) |
| Audio in and out, and the handset problem | [docs/audio.md](docs/audio.md) |
| The three indicators, and why three | [docs/indicators.md](docs/indicators.md) |
| **Component values, with derivations** | [docs/values.md](docs/values.md) |
| Part numbers, footprints, what is in stock | [docs/sourcing.md](docs/sourcing.md) |
| **Power sheet, every connection** | [docs/power-sheet.md](docs/power-sheet.md) |
| **Seed sheet, every connection** | [docs/seed-sheet.md](docs/seed-sheet.md) |
| **Panel I/O sheet, every connection** | [docs/panel-io-sheet.md](docs/panel-io-sheet.md) |
| **How to build an instrument on this board** | [docs/integration.md](docs/integration.md) |
| Board-support firmware (MIT) | [firmware/](firmware/) |
| What to do before and during capture | [docs/capture-checklist.md](docs/capture-checklist.md) |
| Datasheets, links and document numbers | [docs/datasheets.md](docs/datasheets.md) |
| Why things are the way they are | [docs/decisions/](docs/decisions/) |

**`docs/pins.yaml` is the source of truth.** The markdown table is generated:

```sh
python3 tools/gen_pinmap.py           # rewrite docs/pinmap.md
python3 tools/gen_pinmap.py --check   # fail if stale
```

Never edit `pinmap.md` by hand. A pin map kept in two places will disagree the
first time a connector moves.

## Terms

**DNP — "do not populate."** The footprint is on the board, the symbol is in the
schematic, the connections exist in the netlist, but **no component is soldered
there**. A deliberately empty position.

It is the mechanism this whole board rests on. caryatid lays out every option any
of its instruments might need and each build populates only its own; without DNP
that would be three different boards. Also written DNI (do not install), NF (not
fitted), or NP.

Since JLCPCB now fits the through-hole parts too, **DNP is an instruction someone
acts on and bills for**, not a note to self. See
[sourcing.md](docs/sourcing.md) for the rule about which things may be DNP and
which never are.

## What "frozen" means

An instrument may leave a pin unpopulated, and may choose between the alternates
listed for a pin. It may **not** repurpose one. The entire value of the platform
is that one layout serves every build; a pin reassigned for one instrument is a
board that no longer serves the others.

The map is **fully allocated**. `D30` is the only spare. Adding anything means
taking it from something else, and the decision records say what that would
cost.

## The fixed core

Populated on every build:

- Barrel jack → SS34 → **bq24074** charger with power path, ISET 890 Ω (1 A)
- **On-board 18650 holder (BT1)**, the only path to `VBAT` — a soldered holder
  cannot be wired backwards. Protected cell or protection PCB **required**
- **TPS61023** boost → **5.0 V** → ferrite + 100 µF → Seed VIN
- Illuminated latching power switch (3–9 V lamp, so `R_LED` is a 0 Ω link)
- `/CHG` + `/PGOOD` panel LEDs — the indication that works with the Seed off
- RGB status LED, battery gauge on A10, charge-status code on A11
- Daisy Seed on 2×(1×20) female headers, machine-fitted
- 74HC14 Schmitt debounce, SMT — see [ADR 0007](docs/decisions/0007-rc-and-schmitt-instead-of-the-ls18-p.md)
- Audio out; audio in laid out on every board, DNP where unused

## Two things worth knowing before you read the map

**Comms ports carry signals, not protocols.** D11/D12 are simultaneously I2C1
and UART4, so the same connector is an I2C sensor, a MIDI input, or an ESP32
bridge depending on what you plug in. Two ports is the ceiling — there is no
third UART on free pins. See [ADR 0003](docs/decisions/0003-comms-ports-are-protocol-agnostic.md).

**D8 is the only free SPI1 clock on the board.** Not a preference — `PA5` is the
only alternative and it is an analogue panel input. An earlier draft spent D8 on
an LED, which would have left SPI1 as two pins with nothing to clock them. See
[ADR 0004](docs/decisions/0004-keep-spi1-drop-the-soft-latch.md).

## Licence

**Settled 2026-08-18.** The hardware and the tools are strongly reciprocal; the
board-support layer deliberately is not:

| What | Licence |
| --- | --- |
| **Hardware** — schematics, PCB, footprints, artwork | **CERN-OHL-S v2** |
| **Tools** — everything in `tools/` | **GPL-3.0-or-later** |
| **Board support** — everything in `firmware/` | **MIT** |

Terms and what counts as *Complete Source* are in [LICENSING.md](LICENSING.md); how
it was reached, and the audit of every design input, are in
[ADR 0006](docs/decisions/0006-licensing-is-open.md).

CERN-OHL-S defines Complete Source as the **editable design files**, so shipping
Gerbers alone does not discharge the obligation. `CERN-OHL-S v2` and
`github.com/ideocentric/caryatid` are both printed on the front silkscreen.

The question this turned on — whether the schematic derived from Adafruit's
reference designs (CC BY-SA, and irreversible) or was drawn independently from
the TI datasheets — was answered **2026-08-08, before capture began**: drawn from
the datasheets. That is what kept the reciprocal option available.

**`firmware/` is MIT on purpose.** A copyleft board-support layer is viral into
anything that links it, which would settle every instrument's firmware licence
from underneath — a decision belonging to each instrument, not to the carrier
board. libDaisy and DaisySP are MIT already.

## Consuming this board

Each instrument takes it as a submodule:

```sh
git submodule add https://github.com/ideocentric/caryatid.git hardware/platform
```

loa consumes it this way at `hardware/platform`. Then add the board support to
your build:

```make
C_INCLUDES  += -Ihardware/platform/firmware/include
CPP_SOURCES += hardware/platform/firmware/src/caryatid.cpp
```

**Read [docs/integration.md](docs/integration.md) first** — it covers what the
board provides, what the instrument must provide, the electrical and mechanical
requirements, and the four things about this board that are not guessable from
a pin number.