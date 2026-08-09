# caryatid

A common power and I/O board for Daisy Seed instruments — absonus, loa, baby
borg, and whatever comes next.

*A caryatid is a column carved as a figure, bearing the weight of what stands on
it. Named for the role rather than for any instrument it carries: calling it
after one of them would have implied it belonged to that one.*

**One PCB layout serves every build.** Every variable element — pots, keypad,
sensors, switches, comms — enters through a connector, and each instrument
populates the subset it needs. Order once, stuff per instrument.

Status: **pin map frozen, KiCad skeleton in place, no schematic content yet.**
See [hardware/pcb/](hardware/pcb/).

## Start here

| | |
| --- | --- |
| **The frozen pin map** | [docs/pinmap.md](docs/pinmap.md) — generated from [docs/pins.yaml](docs/pins.yaml) |
| Connectors and what plugs into them | [docs/connectors.md](docs/connectors.md) |
| Audio in and out, and the handset problem | [docs/audio.md](docs/audio.md) |
| The three indicators, and why three | [docs/indicators.md](docs/indicators.md) |
| **Component values, with derivations** | [docs/values.md](docs/values.md) |
| Part numbers, footprints, what is in stock | [docs/sourcing.md](docs/sourcing.md) |
| **Power sheet, every connection** | [docs/power-sheet.md](docs/power-sheet.md) |
| What to do before and during capture | [docs/capture-checklist.md](docs/capture-checklist.md) |
| Why things are the way they are | [docs/decisions/](docs/decisions/) |

**`docs/pins.yaml` is the source of truth.** The markdown table is generated:

```sh
python3 tools/gen_pinmap.py           # rewrite docs/pinmap.md
python3 tools/gen_pinmap.py --check   # fail if stale
```

Never edit `pinmap.md` by hand. A pin map kept in two places will disagree the
first time a connector moves.

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
- 18650 via JST-PH — protected cell or protection PCB **required**
- **TPS61023** boost → **5.0 V** → ferrite + 100 µF → Seed VIN
- Illuminated latching power switch (3–9 V lamp, so `R_LED` is a 0 Ω link)
- `/CHG` + `/PGOOD` panel LEDs — the indication that works with the Seed off
- RGB status LED, battery gauge on A10, charge-status code on A11
- Daisy Seed on 2×(1×20) female headers
- LS18-P debounce, socketed
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

**None yet — default copyright, all rights reserved.** This is deliberate and
temporary; see [ADR 0006](docs/decisions/0006-licensing-is-open.md). It turns on
whether the schematic derives from Adafruit's reference designs (CC BY-SA, and
irreversible) or is drawn independently from the TI datasheets (every licence
stays open). **Answer that before schematic capture begins**, because the answer
stops being available once it does.

## Consuming this board

Each instrument takes it as a submodule:

```sh
git submodule add <url> hardware/platform
```

No remote exists yet.