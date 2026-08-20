// SPDX-License-Identifier: MIT
// caryatid -- board support for the Daisy Seed carrier
//
// Wraps libDaisy for the things this board does that a bare Seed does not:
// the analogue panel bus, the hardware-debounced switches, the two
// protocol-agnostic comms ports, the on-board battery gauge and charge-status
// code, and the RGB status LED.
//
// It exists because four of those have a polarity, a scale factor or an
// ordering that is not guessable from the pin number, and every instrument
// would otherwise rediscover them:
//
//   - the RGB is COMMON ANODE TO 5 V and the GPIOs sink, so low means lit
//   - the switches pass through a 74HC14 INVERTER, so high means pressed
//   - the battery gauge is behind a 100k/100k divider, so volts are 2x the pin
//   - J5's wipers are A0-A3 then A6-A9, which is not A0..A7
//
// This is a STUB. It compiles against libDaisy and is structured for an
// instrument to build on, but it has not been run on hardware -- no board
// exists yet. Treat every constant as checked against the schematic (they are)
// and every timing as unverified (it is).
//
// Pin definitions come from caryatid_pins.h, generated from docs/pins.yaml.
// Do not write pin numbers here.

#pragma once

#include <cstdint>

#include "daisy_seed.h"
#include "caryatid_pins.h"

namespace caryatid {

// D11/D12. Mutually exclusive by POPULATION -- the board lays out both and a
// build fits one. Choosing here must match what is actually soldered.
enum class CommsA {
    Unused,
    I2C,   // J13a, 4-pin JST-SH, Qwiic/STEMMA-QT pinout
    Uart,  // J13b, 6-pin JST-PH module port -- MIDI, ESP32 bridge, whatever
};

// D13/D14. Also mutually exclusive by population, and note the crossing:
// SW1 lands on D14 and SW2 on D13, not the other way round.
enum class CommsB {
    Unused,
    Uart,      // J15, USART1
    Switches,  // J6 as SW1, J7 as SW2, both via the 74HC14
};

// A11 encodes /CHG and /PGOOD as four voltage levels. See docs/indicators.md.
enum class Charge {
    Unknown,              // reading fell outside every band
    OnBattery,            // 3.300 V -- both high-Z, no external supply
    ExternalNotCharging,  // 2.200 V -- /PGOOD low, charge complete or idle
    Charging,             // 1.650 V -- /CHG low
    ChargingExternal,     // 1.320 V -- both low
};

enum class Switch { SW1, SW2, SW3 };

struct Config {
    CommsA comms_a = CommsA::Unused;
    CommsB comms_b = CommsB::Unused;

    // Populate only what the instrument actually fits. An unpopulated analogue
    // input is a floating ADC pin: it reads noise, not zero.
    bool panel_analog = true;   // J5, eight wipers
    bool panel_digital = true;  // J11, seven lines
    bool fsr = false;           // J10, A4, 10k pulldown
    bool soft_pot = false;      // J9,  A5, 3k pulldown
    bool rgb = true;            // J12
};

class Caryatid {
  public:
    // Call once, after seed.Init(). Starts the ADC over whichever channels the
    // config enables, plus the two always-present on-board ones.
    void Init(daisy::DaisySeed &seed, const Config &cfg = Config{});

    // Call at control rate -- 1 kHz is the design point the panel RC networks
    // were sized for (1k/100nF corners at 455 Hz). Drives switch edge
    // detection and the software PWM behind Rgb().
    void Update();

    // --- Sensors ----------------------------------------------------------
    // 0..1. Index is CONNECTOR ORDER on J5, not caryatid pin order.
    float Panel(int i) const;
    float Fsr() const;      // pressure. Rises with force.
    float SoftPot() const;  // position. Floats when untouched -- see IsTouched.
    bool  SoftPotTouched(float threshold = 0.02f) const;

    // --- Switches ---------------------------------------------------------
    // True while pressed. The 74HC14 inverts, so this is already right way up.
    bool Pressed(Switch s) const;
    bool RisingEdge(Switch s) const;   // pressed this Update(), not last
    bool FallingEdge(Switch s) const;

    // J11 lines, raw GPIO with 100 ohm series. No pull-up and no debounce on
    // the board -- these are keypad scan lines, so they may be driven as
    // outputs instead. Index is connector order.
    bool DigitalIn(int i) const;
    void DigitalOut(int i, bool high);
    void SetDigitalDirection(int i, bool output);

    // --- Power ------------------------------------------------------------
    float  BatteryVolts() const;  // cell volts, divider already undone
    Charge ChargeState() const;

    // --- Indicator --------------------------------------------------------
    // 0..1 per channel. Common anode is handled: 1.0 is fully lit.
    // Green and blue are brighter per milliamp than red -- equal values do not
    // give a neutral white. Tune by eye, per docs/indicators.md.
    void Rgb(float r, float g, float b);

    // --- Comms ------------------------------------------------------------
    // Only valid when Config selected the matching mode; asserts otherwise in
    // debug builds and returns a dead handle in release. Check Has*() first.
    bool HasI2C() const { return cfg_.comms_a == CommsA::I2C; }
    bool HasUartA() const { return cfg_.comms_a == CommsA::Uart; }
    bool HasUartB() const { return cfg_.comms_b == CommsB::Uart; }
    bool HasSwitchesB() const { return cfg_.comms_b == CommsB::Switches; }

    daisy::I2CHandle    &I2C() { return i2c_; }
    daisy::UartHandler  &UartA() { return uart_a_; }
    daisy::UartHandler  &UartB() { return uart_b_; }

    // D8/D9/D10 + D30 as chip select. D8 is the ONLY free SPI1 clock on the
    // board -- do not spend it on anything else.
    daisy::SpiHandle &Expansion() { return spi_; }

  private:
    struct Deb {
        bool state = false, prev = false;
        uint8_t run = 0;   // consecutive agreeing samples
    };

    float  AdcFloat(int seed_pin) const;
    void   UpdateSwitch(Deb &d, bool raw);

    daisy::DaisySeed *seed_ = nullptr;
    Config            cfg_{};

    // ADC channel index per enabled input, -1 when not populated.
    int   adc_panel_[ANALOG_PANEL_COUNT];
    int   adc_fsr_ = -1, adc_soft_ = -1, adc_batt_ = -1, adc_charge_ = -1;

    daisy::GPIO gpio_digital_[DIGITAL_PANEL_COUNT];
    bool        digital_is_output_[DIGITAL_PANEL_COUNT] = {};

    daisy::GPIO gpio_sw1_, gpio_sw2_, gpio_sw3_;
    Deb         sw1_, sw2_, sw3_;

    daisy::GPIO gpio_r_, gpio_g_, gpio_b_;
    float       rgb_[3] = {0.f, 0.f, 0.f};
    uint8_t     pwm_phase_ = 0;

    daisy::I2CHandle   i2c_;
    daisy::UartHandler uart_a_, uart_b_;
    daisy::SpiHandle   spi_;
};

}  // namespace caryatid