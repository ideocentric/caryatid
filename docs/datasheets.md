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

## The compute module

The Seed is not on the BOM — it plugs into A1/A2 — but the pin map is derived
from its documentation, so the documentation is load-bearing.

| Part | Document | Rev | Local file |
| --- | --- | --- | --- |
| Electrosmith **Daisy Seed** | datasheet | **v1.2.0** | `Daisy_Seed_datasheet.pdf` |
| — schematic, **redacted** | ES_Daisy_Seed_Rev7 | Feb 2024 | `ES_Daisy_Seed_Rev7.pdf` |
| — pinout drawing | Daisy_Seed_pinout-25 | — | `Daisy_Seed_pinout-25.pdf` |
| — pinout table, 40 pins | Seed_pinout.csv | — | `Seed_pinout.csv` |
| ST **STM32H750IBK6** | `DS12556` | **Rev 8**, Jan 2026 | `stm32h750ib.pdf` |
| Wolfson/Cirrus **WM8731** codec | `WM8731/WM8731L` | **PD Rev 4.0**, Feb 2005 | `WM8731_PD_rev4.0.pdf` |

- Daisy Seed — <https://docs.daisy.audio/hardware/Seed/> links all four; the files
  themselves are under
  `https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/`
- STM32H750 — <https://www.st.com/resource/en/datasheet/stm32h750ib.pdf>
- WM8731 — Cirrus no longer hosts it prominently; a copy is at
  <https://cdn.sparkfun.com/datasheets/Dev/Arduino/Shields/WolfsonWM8731.pdf>

**The codec was missing from this file until 2026-08-21**, which was a real gap:
every audio-input decision in [audio.md](audio.md) depends on its input gain,
and there was nothing here to check it against.

### WM8731 input gain — confirmed 2026-08-21

Read from Table 3 and the Electrical Characteristics, PD Rev 4.0:

| Path | Register | Range |
| --- | --- | --- |
| **Line input PGA** | `LINVOL[4:0]` R0 (00h), `RINVOL[4:0]` R1 (02h) | `11111` = **+12 dB**, 1.5 dB steps, `00000` = −34.5 dB. Default `10111` = 0 dB |
| Mic path, nominal | `MICBOOST = 0` | **14 dB** |
| Mic path, boosted | `MICBOOST = 1`, R4 (08h) bit 0 | **34 dB** |

The **+12 dB line figure is what [audio.md](audio.md) relies on** for the
dynamic-capsule case, and it holds: ×250 in the MCP6002 is 47.96 dB, plus 12 dB
is 60 dB, and at ×250 the MCP6002's 1 MHz GBW puts −3 dB at 4 kHz — above the
3.4 kHz voiceband edge.

**The mic path is a much larger reserve — 34 dB — but caryatid cannot reach it**
unless the Seed brings `MICIN` out, and the Seed's audio pins are documented as
line level. Treat 34 dB as unavailable until the Seed schematic says otherwise;
it is recorded here so the question is not re-derived.

**The Daisy documents are MIT licensed.** The datasheet carries the MIT text in
its colophon, covering "the Software and associated documentation files". Unlike
the four IC datasheets above, these *can* be committed to a public repository if
the licence notice goes with them. They are in `local/` only for consistency.

**st.com could not be reached from tooling** — it refuses both a plain fetch and
a browser-headed request, where TI, Nexperia, Microchip and the Daisy CDN all
succeed. `stm32h750ib.pdf` was downloaded by hand. Worth knowing before anyone
tries to script this.

Two cautions about the Seed documents:

- **The schematic is redacted and omits the MCU.** It shows the headers, USB, the
  TPS62170 buck, the LP2985 analogue LDO and the codec, but the STM32 is not on
  it. The part number is not confirmable from Electrosmith's own published
  schematic; it comes from `DS12556`'s package list matching the module and from
  secondary sources.
- **`Seed_pinout.csv` does not mark 5 V tolerance.** It gives Daisy pin → STM32
  pin → primary and alternate functions, and that is the authority behind
  [pins.yaml](pins.yaml). The claim in [indicators.md](indicators.md) that D26,
  D27 and D29 are `FT` has to come from the pin-definitions table in `DS12556`,
  which is now on file and can be checked.

## Not yet gathered

| Part | Why it matters | Status |
| --- | --- | --- |
| MPD **BH-18650-PC** holder | 21.31 mm height sets the enclosure stack; rated for protected cells | drawing cited in [sourcing.md](sourcing.md); **no file** |
| RGB LED `B01C19ENFK` | forward voltages 3.0–3.2 V green and blue, the reason it needs 5 V | vendor specification quoted; **no datasheet** |
| Bicolour LED `B01CFZMO3I` | the green die decides whether J4 works at all | **UNVERIFIED** — see [sourcing.md](sourcing.md) |

The last one is the open question, not merely a missing file: J4 hangs on
`VOUT`, so a 3.0 V green will go dark as the cell drains.