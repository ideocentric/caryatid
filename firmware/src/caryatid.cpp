// SPDX-License-Identifier: MIT
// caryatid board support -- implementation.
//
// Every magic number here is traceable to a document in docs/ and is cited at
// the point of use. Nothing was estimated.

#include "caryatid.h"

using namespace daisy;

namespace caryatid {

namespace {

// docs/indicators.md: /CHG and /PGOOD encoded on A11 as four levels, from a
// 10k pull-up to 3V3 and two different-valued pull-downs. Thresholds sit
// midway between adjacent levels; the tightest gap is 330 mV, so a 165 mV
// margin either side. The parts are 0.1% precisely so these bands hold.
constexpr float kVBattery   = 3.300f;   // both high-Z
constexpr float kVExternal  = 2.200f;   // /PGOOD low
constexpr float kVCharging  = 1.650f;   // /CHG low
constexpr float kVBoth      = 1.320f;   // both low

constexpr float kAdcFullScale = 3.3f;   // Seed ADC reference

// docs/values.md: A10 sits behind 100k/100k from BAT, so the pin sees half.
constexpr float kBatteryDivider = 2.0f;

// Consecutive agreeing samples before a switch state is accepted. The RC into
// the 74HC14 already removes contact bounce in hardware -- 220 nF for a panel
// switch, 1 uF for a hook lever -- so this is only guarding against a sample
// landing exactly on an edge. It is deliberately small; making it large would
// add latency to solve a problem the board already solved.
constexpr uint8_t kDebounceSamples = 2;

// Software PWM depth for the RGB. These pins are not on convenient timer
// channels, so brightness is dithered in Update() instead. At a 1 kHz control
// rate this gives ~64 Hz refresh, which is visible as flicker if you move your
// eyes across it. Fine for a status indicator, not for anything animated.
constexpr uint8_t kPwmSteps = 16;

}  // namespace

void Caryatid::Init(DaisySeed &seed, const Config &cfg) {
    seed_ = &seed;
    cfg_  = cfg;

    // ---- ADC -------------------------------------------------------------
    // One contiguous channel list. Order here defines the index passed to
    // adc.GetFloat(), so it is recorded into the adc_* members as we go rather
    // than assumed to match anything.
    AdcChannelConfig ch[12];
    int n = 0;

    for (int i = 0; i < ANALOG_PANEL_COUNT; ++i) adc_panel_[i] = -1;
    if (cfg_.panel_analog) {
        for (int i = 0; i < ANALOG_PANEL_COUNT; ++i) {
            ch[n].InitSingle(seed.GetPin(ANALOG_PANEL[i]));
            adc_panel_[i] = n++;
        }
    }
    if (cfg_.fsr) {
        ch[n].InitSingle(seed.GetPin(FSR_AUX_ANALOG));
        adc_fsr_ = n++;
    }
    if (cfg_.soft_pot) {
        ch[n].InitSingle(seed.GetPin(SOFT_POT_AUX_ANALOG));
        adc_soft_ = n++;
    }
    // Always present: both are on-board, not behind a connector, and cost
    // nothing to read. The battery divider draws ~21 uA continuously whether
    // firmware looks at it or not.
    ch[n].InitSingle(seed.GetPin(BATTERY_GAUGE));
    adc_batt_ = n++;
    ch[n].InitSingle(seed.GetPin(CHARGE_STATUS_CODE));
    adc_charge_ = n++;

    seed.adc.Init(ch, n);
    seed.adc.Start();

    // ---- Digital panel ---------------------------------------------------
    if (cfg_.panel_digital) {
        for (int i = 0; i < DIGITAL_PANEL_COUNT; ++i) {
            // Default to input with pull-up. The board has 100 ohm series and
            // no pull -- a floating input reads noise, and on loa these are
            // keypad scan lines where the idle state must be defined.
            gpio_digital_[i].Init(seed.GetPin(DIGITAL_PANEL[i]),
                                  GPIO::Mode::INPUT, GPIO::Pull::PULLUP);
            digital_is_output_[i] = false;
        }
    }

    // ---- Switches --------------------------------------------------------
    // SW3 is always available; it does not share pins with anything.
    gpio_sw3_.Init(seed.GetPin(SW3_VIA_74HC14), GPIO::Mode::INPUT);
    if (cfg_.comms_b == CommsB::Switches) {
        // The crossing is real: SW1 is on D14, SW2 on D13.
        gpio_sw1_.Init(seed.GetPin(COMMS_PORT_B_SIGNAL_2), GPIO::Mode::INPUT);
        gpio_sw2_.Init(seed.GetPin(COMMS_PORT_B_SIGNAL_1), GPIO::Mode::INPUT);
    }

    // ---- RGB -------------------------------------------------------------
    // Common anode to the 5 V rail with the GPIO sinking, so the pin must be
    // able to sit high without sourcing into the LED. Start dark: write HIGH.
    if (cfg_.rgb) {
        gpio_r_.Init(seed.GetPin(RGB_STATUS_RED), GPIO::Mode::OUTPUT);
        gpio_g_.Init(seed.GetPin(RGB_STATUS_GREEN), GPIO::Mode::OUTPUT);
        gpio_b_.Init(seed.GetPin(RGB_STATUS_BLUE), GPIO::Mode::OUTPUT);
        gpio_r_.Write(true);
        gpio_g_.Write(true);
        gpio_b_.Write(true);
    }

    // ---- Comms A, D11/D12 ------------------------------------------------
    if (cfg_.comms_a == CommsA::I2C) {
        I2CHandle::Config c;
        c.periph = I2CHandle::Config::Peripheral::I2C_1;
        c.speed  = I2CHandle::Config::Speed::I2C_400KHZ;
        c.mode   = I2CHandle::Config::Mode::I2C_MASTER;
        c.pin_config.scl = seed.GetPin(COMMS_PORT_A_SIGNAL_1);  // D11
        c.pin_config.sda = seed.GetPin(COMMS_PORT_A_SIGNAL_2);  // D12
        i2c_.Init(c);
    } else if (cfg_.comms_a == CommsA::Uart) {
        UartHandler::Config c;
        c.periph    = UartHandler::Config::Peripheral::UART_4;
        c.mode      = UartHandler::Config::Mode::TX_RX;
        c.baudrate  = 31250;  // MIDI. Override before Init for anything else.
        c.pin_config.rx = seed.GetPin(COMMS_PORT_A_SIGNAL_1);  // D11, UART4_RX
        c.pin_config.tx = seed.GetPin(COMMS_PORT_A_SIGNAL_2);  // D12, UART4_TX
        uart_a_.Init(c);
    }

    // ---- Comms B, D13/D14 ------------------------------------------------
    if (cfg_.comms_b == CommsB::Uart) {
        UartHandler::Config c;
        c.periph   = UartHandler::Config::Peripheral::USART_1;
        c.mode     = UartHandler::Config::Mode::TX_RX;
        c.baudrate = 31250;
        c.pin_config.tx = seed.GetPin(COMMS_PORT_B_SIGNAL_1);  // D13, USART1_TX
        c.pin_config.rx = seed.GetPin(COMMS_PORT_B_SIGNAL_2);  // D14, USART1_RX
        uart_b_.Init(c);
    }

    // ---- Expansion SPI1, D8/D9/D10 + D30 as CS ---------------------------
    {
        SpiHandle::Config c;
        c.periph    = SpiHandle::Config::Peripheral::SPI_1;
        c.mode      = SpiHandle::Config::Mode::MASTER;
        c.direction = SpiHandle::Config::Direction::TWO_LINES;
        c.datasize  = 8;
        c.nss       = SpiHandle::Config::NSS::SOFT;
        c.pin_config.sclk = seed.GetPin(EXPANSION_SCLK);
        c.pin_config.miso = seed.GetPin(EXPANSION_MISO);
        c.pin_config.mosi = seed.GetPin(EXPANSION_MOSI);
        c.pin_config.nss  = seed.GetPin(SPARE_EXPANSION_CS);
        spi_.Init(c);
    }
}

float Caryatid::AdcFloat(int idx) const {
    if (!seed_ || idx < 0) return 0.f;
    return seed_->adc.GetFloat(idx);
}

void Caryatid::UpdateSwitch(Deb &d, bool raw) {
    d.prev = d.state;
    if (raw == d.state) {
        d.run = 0;
        return;
    }
    if (++d.run >= kDebounceSamples) {
        d.state = raw;
        d.run   = 0;
    }
}

void Caryatid::Update() {
    if (!seed_) return;

    // The 74HC14 inverts: switch closed pulls its input to ground, so the
    // output -- and therefore the GPIO -- reads HIGH when pressed.
    UpdateSwitch(sw3_, gpio_sw3_.Read());
    if (cfg_.comms_b == CommsB::Switches) {
        UpdateSwitch(sw1_, gpio_sw1_.Read());
        UpdateSwitch(sw2_, gpio_sw2_.Read());
    }

    if (cfg_.rgb) {
        // Software PWM. Writing LOW lights the LED, hence the inversion on
        // every Write below -- common anode to 5 V, GPIO sinking.
        pwm_phase_ = (pwm_phase_ + 1) % kPwmSteps;
        const auto lit = [&](float v) {
            if (v <= 0.f) return false;
            if (v >= 1.f) return true;
            return pwm_phase_ < static_cast<uint8_t>(v * kPwmSteps);
        };
        gpio_r_.Write(!lit(rgb_[0]));
        gpio_g_.Write(!lit(rgb_[1]));
        gpio_b_.Write(!lit(rgb_[2]));
    }
}

float Caryatid::Panel(int i) const {
    if (i < 0 || i >= ANALOG_PANEL_COUNT) return 0.f;
    return AdcFloat(adc_panel_[i]);
}

float Caryatid::Fsr() const { return AdcFloat(adc_fsr_); }
float Caryatid::SoftPot() const { return AdcFloat(adc_soft_); }

bool Caryatid::SoftPotTouched(float threshold) const {
    // A SoftPot wiper floats when untouched; the 3k pulldown gives it a
    // defined near-zero reading instead. Anything above the floor is a touch.
    return AdcFloat(adc_soft_) > threshold;
}

bool Caryatid::Pressed(Switch s) const {
    switch (s) {
        case Switch::SW1: return sw1_.state;
        case Switch::SW2: return sw2_.state;
        case Switch::SW3: return sw3_.state;
    }
    return false;
}

bool Caryatid::RisingEdge(Switch s) const {
    switch (s) {
        case Switch::SW1: return sw1_.state && !sw1_.prev;
        case Switch::SW2: return sw2_.state && !sw2_.prev;
        case Switch::SW3: return sw3_.state && !sw3_.prev;
    }
    return false;
}

bool Caryatid::FallingEdge(Switch s) const {
    switch (s) {
        case Switch::SW1: return !sw1_.state && sw1_.prev;
        case Switch::SW2: return !sw2_.state && sw2_.prev;
        case Switch::SW3: return !sw3_.state && sw3_.prev;
    }
    return false;
}

bool Caryatid::DigitalIn(int i) const {
    if (i < 0 || i >= DIGITAL_PANEL_COUNT || digital_is_output_[i]) return false;
    return gpio_digital_[i].Read();
}

void Caryatid::DigitalOut(int i, bool high) {
    if (i < 0 || i >= DIGITAL_PANEL_COUNT || !digital_is_output_[i]) return;
    gpio_digital_[i].Write(high);
}

void Caryatid::SetDigitalDirection(int i, bool output) {
    if (!seed_ || i < 0 || i >= DIGITAL_PANEL_COUNT) return;
    gpio_digital_[i].Init(seed_->GetPin(DIGITAL_PANEL[i]),
                          output ? GPIO::Mode::OUTPUT : GPIO::Mode::INPUT,
                          output ? GPIO::Pull::NOPULL : GPIO::Pull::PULLUP);
    digital_is_output_[i] = output;
}

float Caryatid::BatteryVolts() const {
    return AdcFloat(adc_batt_) * kAdcFullScale * kBatteryDivider;
}

Charge Caryatid::ChargeState() const {
    const float v = AdcFloat(adc_charge_) * kAdcFullScale;
    // Midpoints between adjacent levels. Ordered high to low.
    if (v > (kVBattery + kVExternal) * 0.5f) return Charge::OnBattery;
    if (v > (kVExternal + kVCharging) * 0.5f) return Charge::ExternalNotCharging;
    if (v > (kVCharging + kVBoth) * 0.5f) return Charge::Charging;
    // Below the lowest band centre by more than half a gap means something is
    // wrong -- a shorted pin or an unpopulated network -- not "both low".
    if (v > kVBoth - (kVCharging - kVBoth) * 0.5f) return Charge::ChargingExternal;
    return Charge::Unknown;
}

void Caryatid::Rgb(float r, float g, float b) {
    rgb_[0] = r < 0.f ? 0.f : (r > 1.f ? 1.f : r);
    rgb_[1] = g < 0.f ? 0.f : (g > 1.f ? 1.f : g);
    rgb_[2] = b < 0.f ? 0.f : (b > 1.f ? 1.f : b);
}

}  // namespace caryatid