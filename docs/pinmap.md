# Pin map

<!-- GENERATED FROM docs/pins.yaml BY tools/gen_pinmap.py -- DO NOT EDIT -->

**caryatid** rev A — Daisy Seed (STM32H750IB). Status: **frozen 2026-08-08**.

Frozen means an instrument may leave a pin unpopulated, and may choose
between the alternates listed, but may not repurpose it. One PCB layout
serves every build; only the population changes.

## Analogue

| Pin | Seed | MCU | Role | Connector | Alternate |
| --- | --- | --- | --- | --- | --- |
| `A0` | D15 | PC0 | analog panel 1 | J5 | — |
| `A1` | D16 | PA3 | analog panel 2 | J5 | — |
| `A2` | D17 | PB1 | analog panel 3 | J5 | — |
| `A3` | D18 | PA7 | analog panel 4 | J5 | `SPI1_MOSI` |
| `A4` | D19 | PA6 | FSR / aux analog | J10 | `SPI1_MISO` |
| `A5` | D20 | PC1 | soft pot / aux analog | J9 | — |
| `A6` | D21 | PC4 | analog panel 5 | J5 | — |
| `A7` | D22 | PA5 | analog panel 6 | J5 | `SPI1_SCLK` |
| `A8` | D23 | PA4 | analog panel 7 | J5 | `SPI1_NSS` |
| `A9` | D24 | PA1 | analog panel 8 | J5 | `UART4_RX` |
| `A10` | D25 | PA0 | battery gauge | on-board | `UART4_TX` |
| `A11` | D28 | PA2 | charge-status code | on-board | — |

**Notes**

- **`A4`** — 10k pulldown, **fitted** (ADR 0010; it was a DNP option). NOT 3k -- the platform spec had this transposed with A5, inherited from a stale ribbon-synth doc. The fabricated absonus board has 10k on the FSR and 3k on the soft pot.
- **`A5`** — 3k pulldown, **fitted** (ADR 0010; it was a DNP option). Gives the wiper a defined reading when the pot is untouched -- a SoftPot wiper floats.
- **`A10`** — 100k/100k from BAT + 1k/10nF. ~21 uA continuous drain, always.
- **`A11`** — /CHG and /PGOOD encoded as four voltage levels. See indicators.md.

## Digital

| Pin | Seed | MCU | Role | Connector | Alternate |
| --- | --- | --- | --- | --- | --- |
| `D0` | D0 | PB12 | digital panel 1 | J11 | `UART5_RX` |
| `D1` | D1 | PC11 | digital panel 2 | J11 | `UART4_RX` |
| `D2` | D2 | PC10 | digital panel 3 | J11 | `UART4_TX` |
| `D3` | D3 | PC9 | digital panel 4 | J11 | — |
| `D4` | D4 | PC8 | digital panel 5 | J11 | — |
| `D5` | D5 | PD2 | digital panel 6 | J11 | `UART5_RX` |
| `D6` | D6 | PC12 | digital panel 7 | J11 | `UART5_TX` |
| `D7` | D7 | PG10 | SW3 via 74HC14 | J8 | `SPI1_NSS` |
| `D8` | D8 | PG11 | expansion SCLK | J16 | `SPI1_SCLK` |
| `D9` | D9 | PB4 | expansion MISO | J16 | `SPI1_MISO` |
| `D10` | D10 | PB5 | expansion MOSI | J16 | `SPI1_MOSI` |
| `D11` | D11 | PB8 | comms port A signal 1 | J13 | `I2C1_SCL / UART4_RX` |
| `D12` | D12 | PB9 | comms port A signal 2 | J13 | `I2C1_SDA / UART4_TX` |
| `D13` | D13 | PB6 | comms port B signal 1 | J15, or J6 as SW1 | `USART1_TX / UART5_TX` |
| `D14` | D14 | PB7 | comms port B signal 2 | J15, or J7 as SW2 | `USART1_RX` |
| `D26` | D26 | PD11 | RGB status - red | J12 | — |
| `D27` | D27 | PG9 | RGB status - green | J12 | `SPI1_MISO` |
| `D29` | D29 | PB14 | RGB status - blue | J12 | `SPI2_MISO` |
| `D30` | D30 | PB15 | spare / expansion CS | J16 | — |

**Notes**

- **`D7`** — loa's hook switch lives here, NOT on SW1/SW2 -- those pins are comms port B and USART1 needs both of them.
- **`D8`** — The ONLY free SPI1 clock. PA5 is the sole alternative and it is an analog panel input. Do not spend this pin on an LED.
- **`D30`** — The only genuinely unassigned pin on the board -- and it is brought out to J16 rather than left floating, so 'spare' means usable rather than merely unallocated.

## Counts

- 12 analogue, 19 digital — **31 of 31 Seed pins assigned**
- Spare: `D30`
- Every other pin has a job. Adding one means taking it from something, which is what freezing the map is for.

