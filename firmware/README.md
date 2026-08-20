# firmware — board support for caryatid

Stub board-support code for instruments built on this board. **MIT licensed**,
unlike the rest of the repository, so instrument firmware can link it without
inheriting copyleft — see [../LICENSING.md](../LICENSING.md).

```
firmware/
  include/caryatid_pins.h   GENERATED from docs/pins.yaml — do not edit
  include/caryatid.h        the Caryatid class
  src/caryatid.cpp          implementation
  examples/panel_readout.cpp  bring-up sketch: reads everything, prints it
```

## Status: stub, never run on hardware

**No board has been fabricated yet.** This compiles against libDaisy and is
structured for an instrument to build on, but nothing here has been executed.

The distinction that matters:

- **Every pin, polarity and scale factor is checked against the schematics**
  in `docs/`, and cited at the point of use in the source. Those are as good as
  the documents they come from.
- **Every timing is unverified.** The debounce sample count, the software PWM
  depth, the 1 kHz control rate — all reasoned from the hardware, none measured.

Expect to adjust the second category on first bring-up. Treat a disagreement in
the first category as a bug worth chasing to the schematic.

## What it does that a bare Seed does not

Four things on this board have a polarity, a scale factor or an ordering that
is not guessable from a pin number, and every instrument would otherwise
rediscover them the hard way:

| | |
| --- | --- |
| **RGB status** | Common anode to **5 V**, GPIOs sinking — writing **low** lights it. Green and blue will not light from a 3V3 GPIO at all; their forward voltage is above the output-high level. |
| **Switches** | Pass through a 74HC14 **inverter**, so the GPIO reads **high when pressed**. And SW1 is on `D14` while SW2 is on `D13` — they cross. |
| **Battery gauge** | Behind a 100k/100k divider, so cell volts are **2×** the pin. |
| **J5 analogue bus** | Wipers are `A0`–`A3` then `A6`–`A9`, **not** `A0..A7`. `A4` and `A5` are the dedicated sensor inputs and are not on the bus. |

`Caryatid` handles all four. `caryatid_pins.h` carries the caryatid name, STM32
pin and connector in a comment on every line, because a Seed pin index on its
own tells you nothing at a call site.

## Use

```cpp
#include "daisy_seed.h"
#include "caryatid.h"

DaisySeed          seed;
caryatid::Caryatid hw;

int main() {
    seed.Init();

    caryatid::Config cfg;
    cfg.fsr     = true;
    cfg.comms_a = caryatid::CommsA::I2C;       // J13, Qwiic
    cfg.comms_b = caryatid::CommsB::Switches;  // J6/J7 as SW1/SW2
    hw.Init(seed, cfg);

    while (1) {
        hw.Update();                  // control rate, ~1 kHz
        System::Delay(1);

        float cutoff = hw.Panel(0);   // J5 connector order
        if (hw.RisingEdge(caryatid::Switch::SW3)) { /* hook lifted */ }
        if (hw.BatteryVolts() < 3.3f) hw.Rgb(1, 0, 0);
    }
}
```

**`Config` must match what is actually soldered.** The board lays out both
options for each comms port and a build fits one; selecting the wrong mode
configures a peripheral onto pins that are not connected, and it fails silently.
An unpopulated analogue input is a floating ADC pin — it reads noise, not zero.

## Building

There is no build system here on purpose. This is a **source drop**, consumed
by an instrument repo that already has libDaisy, a linker script and a
bootloader target. Adding a second build system would mean maintaining one that
nothing exercises.

Consume it as a submodule and add to your Makefile:

```make
C_INCLUDES += -Ihardware/platform/firmware/include
CPP_SOURCES += hardware/platform/firmware/src/caryatid.cpp
```

Requires **libDaisy** on the include path; `daisy_seed.h` must resolve. Editor
diagnostics in this repo will show it unresolved, because libDaisy is vendored
in the instrument repos rather than here.

## Regenerating the pin header

`caryatid_pins.h` is generated. Never edit it.

```sh
.venv/bin/python tools/gen_firmware.py           # rewrite
.venv/bin/python tools/gen_firmware.py --check   # fail if stale
```

`docs/pins.yaml` is the source of truth for the pin map and everything else is
a consumer of it. A pin map kept in two places disagrees the first time a
connector moves — and a firmware header is a far worse place to discover that
than a markdown table, because the board is already built and the symptom is a
sensor quietly reading the wrong wire.

## Licensing

**This directory is MIT.** The rest of the repository is not — the hardware is
CERN-OHL-S-2.0 and `tools/` is GPL-3.0-or-later. See
[../LICENSING.md](../LICENSING.md) for all three.

### Your instrument can still be copyleft

MIT is permissive, so it imposes no condition that a copyleft licence cannot
satisfy. **You may absorb this code into a GPL instrument**: the combined binary
is distributed under the GPL, and the MIT notice is preserved for these files.
The FSF classes MIT as GPL-compatible for exactly this.

This is not theoretical — loa already does it. Its firmware is
GPL-3.0-or-later and links MIT libDaisy and DaisySP today, and its licensing
ADR records the same conclusion. (That repository is private as of this
writing, so there is no link to give.)

| instrument | may be licensed | because |
| --- | --- | --- |
| loa | **GPL-3.0-or-later** (and is) | MIT absorbs into GPL cleanly |
| absonus | GPL, MIT, BSD — anything | MIT imposes no reciprocity |
| baby borg | same | same |

### Why it is not GPL

**The reverse does not work, and that is the whole reason.** A copyleft
board-support layer is viral into everything that links it, so GPL here would
force every instrument built on caryatid to be GPL — settling absonus's and baby
borg's licence from a header file in the carrier board underneath them. That
decision belongs to each instrument.

Permissive at the bottom, copyleft optional at the top. It is the only
arrangement that keeps all three choices open.

### What you owe

1. **Ship the MIT notice** with these files when you distribute instrument
   firmware. Consuming caryatid as a submodule satisfies this already —
   `../LICENSES/MIT.txt` travels with it, and every source file carries an
   `SPDX-License-Identifier`.
2. **It cuts both ways.** Anyone may take this directory alone and use it in a
   closed product. That is the price of not constraining the instruments.

The reciprocity that matters is on the **board**, not here: CERN-OHL-S defines
*Complete Source* as the editable design files, so nobody ships derivative
hardware without publishing the KiCad project. A permissive stub layer does not
weaken that.

## Reference

| | |
| --- | --- |
| Pin map | [../docs/pinmap.md](../docs/pinmap.md), generated from `pins.yaml` |
| What plugs into what | [../docs/connectors.md](../docs/connectors.md) |
| Integration guide | [../docs/integration.md](../docs/integration.md) |
| Charge-status encoding | [../docs/indicators.md](../docs/indicators.md) |
| Component values and derivations | [../docs/values.md](../docs/values.md) |