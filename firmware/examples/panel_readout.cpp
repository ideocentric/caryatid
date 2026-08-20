// SPDX-License-Identifier: MIT
// caryatid -- minimal bring-up sketch.
//
// Reads everything the board offers and prints it over USB serial once a
// second, while showing charge state on the RGB. This is the thing to flash
// first on a new board: it exercises every subsystem, so anything mis-soldered
// shows up as a wrong number rather than as a silent failure later.
//
// Build: see ../README.md. libDaisy must be on the include path.

#include "daisy_seed.h"
#include "caryatid.h"

using namespace daisy;

DaisySeed          seed;
caryatid::Caryatid hw;

int main(void) {
    seed.Init();
    seed.StartLog(false);  // false = do not block waiting for a terminal

    caryatid::Config cfg;
    cfg.panel_analog  = true;
    cfg.panel_digital = true;
    cfg.fsr           = true;
    cfg.soft_pot      = true;
    // Pick ONE per port, and it must match what is soldered. See
    // docs/connectors.md -- the board lays out both options and a build fits
    // one, so choosing the wrong one here reads a pin that is not connected.
    cfg.comms_a = caryatid::CommsA::I2C;        // J13, Qwiic sensor
    cfg.comms_b = caryatid::CommsB::Switches;   // J6/J7 as SW1/SW2

    hw.Init(seed, cfg);

    uint32_t last_print = System::GetNow();

    while (1) {
        // Control rate. The panel RC networks corner at 455 Hz, so sampling
        // faster than ~1 kHz buys nothing.
        hw.Update();
        System::Delay(1);

        // Charge state on the RGB, per docs/indicators.md. Green and blue read
        // brighter than red at equal current -- tune by eye, do not assume
        // equal values give neutral white.
        switch (hw.ChargeState()) {
            case caryatid::Charge::OnBattery:           hw.Rgb(0, 0, 0); break;
            case caryatid::Charge::Charging:
            case caryatid::Charge::ChargingExternal:    hw.Rgb(0, 0, 1); break;
            case caryatid::Charge::ExternalNotCharging: hw.Rgb(0, 1, 0); break;
            case caryatid::Charge::Unknown:             hw.Rgb(1, 0, 1); break;
        }

        if (System::GetNow() - last_print < 1000) continue;
        last_print = System::GetNow();

        seed.PrintLine("--- caryatid ---");

        // J5 wipers, in CONNECTOR order. Index 0 is J5 pin 2 (caryatid A0),
        // index 4 is J5 pin 6 (caryatid A6) -- the bus is not A0..A7.
        for (int i = 0; i < caryatid::ANALOG_PANEL_COUNT; ++i)
            seed.PrintLine("panel %d: " FLT_FMT3, i, FLT_VAR3(hw.Panel(i)));

        seed.PrintLine("fsr:      " FLT_FMT3, FLT_VAR3(hw.Fsr()));
        seed.PrintLine("softpot:  " FLT_FMT3 " touched=%d",
                       FLT_VAR3(hw.SoftPot()), hw.SoftPotTouched());

        for (int i = 0; i < caryatid::DIGITAL_PANEL_COUNT; ++i)
            seed.PrintLine("digital %d: %d", i, hw.DigitalIn(i));

        // High means pressed: the 74HC14 inverts. If these read inverted from
        // what you expect, the switch is wired across the wrong J6/J7 pins,
        // not the firmware.
        seed.PrintLine("SW3: %d", hw.Pressed(caryatid::Switch::SW3));
        if (hw.HasSwitchesB()) {
            // SW1 is on D14 and SW2 on D13 -- they cross. Handled inside.
            seed.PrintLine("SW1: %d  SW2: %d",
                           hw.Pressed(caryatid::Switch::SW1),
                           hw.Pressed(caryatid::Switch::SW2));
        }

        // Cell volts, divider already undone. A reading near zero while the
        // board is clearly powered means the cell is disconnected or its
        // protection has tripped -- worth catching before a gig.
        seed.PrintLine("battery:  " FLT_FMT3 " V", FLT_VAR3(hw.BatteryVolts()));
    }
}