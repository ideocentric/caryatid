// SPDX-License-Identifier: MIT
// caryatid -- pin definitions for the Daisy Seed carrier board
//
// GENERATED FROM docs/pins.yaml BY tools/gen_firmware.py -- DO NOT EDIT.
// Edit the yaml and regenerate:  .venv/bin/python tools/gen_firmware.py
//
// Values are DAISY SEED pin indices, ready for seed.GetPin(n). They are NOT
// the caryatid pin names: caryatid A0 is Seed pin 15. The caryatid name is in
// the comment on every line, because that is what the silkscreen, the
// schematic and docs/pinmap.md all use.
//
// THE PIN MAP IS FROZEN. An instrument may leave a pin unpopulated and may
// choose between the alternates listed, but may not repurpose one -- the whole
// value of the platform is that one PCB layout serves every build.

#pragma once

namespace caryatid {

// ------------------------------------------------------------------------
// Analogue -- all twelve ADC-capable pins
// ------------------------------------------------------------------------
constexpr int ANALOG_PANEL_1      = 15;  // A0   PC0   J5
constexpr int ANALOG_PANEL_2      = 16;  // A1   PA3   J5
constexpr int ANALOG_PANEL_3      = 17;  // A2   PB1   J5
constexpr int ANALOG_PANEL_4      = 18;  // A3   PA7   J5, alt SPI1_MOSI
constexpr int FSR_AUX_ANALOG      = 19;  // A4   PA6   J10, alt SPI1_MISO
constexpr int SOFT_POT_AUX_ANALOG = 20;  // A5   PC1   J9
constexpr int ANALOG_PANEL_5      = 21;  // A6   PC4   J5
constexpr int ANALOG_PANEL_6      = 22;  // A7   PA5   J5, alt SPI1_SCLK
constexpr int ANALOG_PANEL_7      = 23;  // A8   PA4   J5, alt SPI1_NSS
constexpr int ANALOG_PANEL_8      = 24;  // A9   PA1   J5, alt UART4_RX
constexpr int BATTERY_GAUGE       = 25;  // A10  PA0   on-board, alt UART4_TX
constexpr int CHARGE_STATUS_CODE  = 28;  // A11  PA2   on-board

// ------------------------------------------------------------------------
// Digital
// ------------------------------------------------------------------------
constexpr int DIGITAL_PANEL_1       =  0;  // D0   PB12  J11, alt UART5_RX
constexpr int DIGITAL_PANEL_2       =  1;  // D1   PC11  J11, alt UART4_RX
constexpr int DIGITAL_PANEL_3       =  2;  // D2   PC10  J11, alt UART4_TX
constexpr int DIGITAL_PANEL_4       =  3;  // D3   PC9   J11
constexpr int DIGITAL_PANEL_5       =  4;  // D4   PC8   J11
constexpr int DIGITAL_PANEL_6       =  5;  // D5   PD2   J11, alt UART5_RX
constexpr int DIGITAL_PANEL_7       =  6;  // D6   PC12  J11, alt UART5_TX
constexpr int SW3_VIA_74HC14        =  7;  // D7   PG10  J8, alt SPI1_NSS
constexpr int EXPANSION_SCLK        =  8;  // D8   PG11  J16, alt SPI1_SCLK
constexpr int EXPANSION_MISO        =  9;  // D9   PB4   J16, alt SPI1_MISO
constexpr int EXPANSION_MOSI        = 10;  // D10  PB5   J16, alt SPI1_MOSI
constexpr int COMMS_PORT_A_SIGNAL_1 = 11;  // D11  PB8   J13, alt I2C1_SCL / UART4_RX
constexpr int COMMS_PORT_A_SIGNAL_2 = 12;  // D12  PB9   J13, alt I2C1_SDA / UART4_TX
constexpr int COMMS_PORT_B_SIGNAL_1 = 13;  // D13  PB6   J15, or J6 as SW1, alt USART1_TX / UART5_TX
constexpr int COMMS_PORT_B_SIGNAL_2 = 14;  // D14  PB7   J15, or J7 as SW2, alt USART1_RX
constexpr int RGB_STATUS_RED        = 26;  // D26  PD11  J12
constexpr int RGB_STATUS_GREEN      = 27;  // D27  PG9   J12, alt SPI1_MISO
constexpr int RGB_STATUS_BLUE       = 29;  // D29  PB14  J12, alt SPI2_MISO
constexpr int SPARE_EXPANSION_CS    = 30;  // D30  PB15  J16

// ------------------------------------------------------------------------
// Bus widths. Hardcoding these at a call site is how a loop walks off the end.
// ------------------------------------------------------------------------

constexpr int ANALOG_PANEL_COUNT  = 8;  // J5, in order on the connector
constexpr int DIGITAL_PANEL_COUNT = 7;  // J11, in order on the connector

// J5 wipers in connector order -- pins 2-5 then 6-9, which is NOT A0..A7.
constexpr int ANALOG_PANEL[ANALOG_PANEL_COUNT] = {
    ANALOG_PANEL_1, ANALOG_PANEL_2, ANALOG_PANEL_3, ANALOG_PANEL_4, ANALOG_PANEL_5, ANALOG_PANEL_6, ANALOG_PANEL_7, ANALOG_PANEL_8
};

// J11 lines in connector order, pins 2-8.
constexpr int DIGITAL_PANEL[DIGITAL_PANEL_COUNT] = {
    DIGITAL_PANEL_1, DIGITAL_PANEL_2, DIGITAL_PANEL_3, DIGITAL_PANEL_4, DIGITAL_PANEL_5, DIGITAL_PANEL_6, DIGITAL_PANEL_7
};

}  // namespace caryatid
