# Datasheets

Every electrical figure in [values.md](values.md) is quoted from one of these,
from the electrical characteristics tables rather than from application notes or
reference designs, so the arithmetic can be checked against the source.

**The PDFs are not in this repository.** They are the manufacturers' copyright,
and being freely downloadable is not the same as being redistributable. Download
them to `local/datasheets/`, which is gitignored, and they are then a hard local
reference that does not depend on a vendor keeping a URL alive. If permission to
redistribute is obtained later, they can move into the repo and this file can
become an index rather than a shopping list.

Filenames below are the convention used in `local/datasheets/`, so that a
citation in the docs leads to a specific file on disk.

## The four ICs

| Ref | Part | Document | Rev | Local file |
| --- | --- | --- | --- | --- |
| U1 | TI **BQ24074RGT** charger | `SLUS810N` | Sep 2008, rev **Oct 2021** | `bq24074_SLUS810N.pdf` |
| U2 | TI **TPS61023DRL** boost | `SLVSF14B` | Sep 2019, rev **Aug 2020** | `tps61023_SLVSF14B.pdf` |
| U3 | Nexperia **74HC14D** Schmitt inverter | 74HC14; 74HCT14 | **Rev. 10**, 29 Feb 2024 | `74HC14_nexperia_rev10.pdf` |
| U4 | Microchip **MCP6002-I/SN** dual op-amp | `DS20001733L` | 2020 | `MCP6001-2-4_DS20001733L.pdf` |

**Links, all verified to resolve:**

- BQ24074 — <https://www.ti.com/lit/ds/symlink/bq24074.pdf>
- TPS61023 — <https://www.ti.com/lit/ds/symlink/tps61023.pdf>
- 74HC14 — <https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf>
- MCP6001/2/4 — <https://ww1.microchip.com/downloads/en/DeviceDoc/MCP6001-1R-1U-2-4-1-MHz-Low-Power-Op-Amp-DS20001733L.pdf>

Each document number above was read off the title page of the file actually
downloaded, not inferred from the part number.

## What each one is load-bearing for

**BQ24074 — `SLUS810N`.** The pin table in [power-sheet.md](power-sheet.md) is
transcribed from **Table 7-1, the '74 column**; the variants differ, and pin 15
is `ITERM` on this one where it is `TD` or `SYSOFF` on others. `EN1`/`EN2` mode
selection is Table 7-2. `KISET = 890 AΩ` sets R3 and therefore the charge
current. The land pattern is drawing **4222419/E**, which the custom footprint
follows. The 7 V absolute maximum on `EN1`/`EN2`/`CE` — the reason `EN2` goes to
`VOUT` and not to the barrel input — is from the absolute maximum ratings.

**TPS61023 — `SLVSF14B`.** `VREF = 595 mV` sets the R7/R8 divider and so the
5.0 V output. `VOVP` minimum of 5.5 V is why the output is 5.0 V rather than
5.2 V — see the margin table in [values.md](values.md). The inductor range
0.37–2.9 µH, the 300 kΩ ceiling on R2 and the 4–20 nA FB leakage all come from
here, as does the 1 MHz switching frequency that makes the `VIN`/L1/`SW`/C6 loop
the one worth keeping small. The title page confirms SOT-563 (DRL), 6-pin.

**74HC14 — Rev. 10.** The debounce in [panel-io-sheet.md](panel-io-sheet.md)
depends on the Schmitt hysteresis, so the part matters and not just the function
— `VT+`/`VT−` differ between manufacturers. The ordering table confirms
**74HC14D is SO14 with a 3.9 mm body**, which is the footprint in use,
`SOIC-14_3.9x8.7mm_P1.27mm`.

**MCP6002 — `DS20001733L`.** The title page carries the two figures quoted in
[sourcing.md](sourcing.md): **1 MHz gain-bandwidth typical** and **1.8 V to 6.0 V
supply**, with rail-to-rail input and output. The gain-bandwidth is what bounds
the usable gain in [audio.md](audio.md).

## Not yet gathered

These are referenced by the design but have no datasheet on file:

| Part | Why it matters | Status |
| --- | --- | --- |
| **Daisy Seed** / STM32H750 | the pin map in [pins.yaml](pins.yaml), and which pins are 5 V tolerant | pin map came from the vendor docs; **no file** |
| MPD **BH-18650-PC** holder | 21.31 mm height sets the enclosure stack; rated for protected cells | drawing cited in [sourcing.md](sourcing.md); **no file** |
| RGB LED `B01C19ENFK` | forward voltages 3.0–3.2 V green and blue, the reason it needs 5 V | vendor specification quoted; **no datasheet** |
| Bicolour LED `B01CFZMO3I` | the green die decides whether J4 works at all | **UNVERIFIED** — see [sourcing.md](sourcing.md) |

The last one is the open question, not merely a missing file: J4 hangs on
`VOUT`, so a 3.0 V green will go dark as the cell drains.