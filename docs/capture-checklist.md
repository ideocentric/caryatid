# Schematic capture checklist

Ordered so the frozen pin map gets **enforced** rather than re-derived. Work
down it; do not skip ahead to the fun part.

## Before opening KiCad

- [ ] **Confirm the licence answer is still "draw from the datasheets."**
      [ADR 0006](decisions/0006-licensing-is-open.md). Once a schematic derives
      from someone else's source file it cannot be un-derived. Nobody opens an
      Adafruit schematic during this work.
- [ ] **Measure the handset capsule** — DC resistance across it decides whether
      the input network gets a preamp or a pad. [audio.md](audio.md).
- [x] ~~Verify D26 / D27 / D29 are 5 V tolerant.~~ **Done** — all three are
      `FT` per Table 7 of `DS12556`. Common anode to 5 V with the GPIOs sinking
      is the scheme; see [values.md](values.md) for the absolute-maximum
      condition and why the pin never actually sees 5 V here.
- [x] ~~Check the bq24074's JLC PCBA type.~~ **Done** — Economic **and**
      Standard, same as the boost. The Economic assembly split holds. Library
      type is unpublished for both; assume Extended and a ~$3 setup fee each,
      which JLC prices when the BOM goes up.
- [ ] **Measure the RGB forward voltages** at the working current, and confirm
      the part is genuinely common anode. Three different series resistors fall
      out of this; a common value is what broke the first scheme.
- [ ] **Buy and measure the mechanical parts.** Switch bezel diameter, jack
      barrel length, IDC and Seed header heights. Together they set the panel
      standoff height, and that number must exist *before* footprints are
      placed, not after.

- [ ] **Reuse the absonus footprints** listed in [sourcing.md](sourcing.md) —
      they are drawn and fabricated already. Check pin-1 orientation and JST
      polarity against *this* schematic; proven to fabricate is not proven
      correct here.

## Sheet structure

Hierarchical, so the power section stays a reusable block for a future board:

- [ ] `power.kicad_sch` — charger, boost, latch, hardware charge LEDs
- [ ] `seed.kicad_sch` — Seed headers, battery gauge, charge-status code
- [ ] `audio.kicad_sch` — jacks, coupling, mic bias and preamp/pad options
- [ ] `panel-io.kicad_sch` — analogue bus, digital bus, switches, comms ports

## Enforcing the pin map

**This is the part that matters.** `docs/pins.yaml` is the source of truth, and
the schematic is a *consumer* of it, not a second opinion.

- [ ] Label every Seed net with the **pin name from `pins.yaml`** — `A7`, `D11`
      — not with what the net does on one instrument. `D11` is not `SCL`; it is
      `D11`, and I2C is one thing it can be.
- [ ] **Cross-check the finished schematic against `pinmap.md` pin by pin.** By
      script if you can face writing one, by eye if not, but do it as a
      distinct pass rather than while drawing.
- [ ] **`D8` is the only free SPI1 clock.** If anything ends up on it that is
      not the expansion header, stop.
- [ ] **Hook switch on `D7`, never `D13`/`D14`.** Those two are comms port B and
      USART1 needs both.

## Power sheet

- [ ] Barrel jack → SS34 → bq24074 `IN`. **5–9 V, never 12 V** — silkscreen it.
- [ ] `RISET` **887 Ω, 1%** — the 1% is a datasheet requirement, not a
      preference; the part short-tests this resistor.
- [ ] `RILIM` **1.2 kΩ** → 1.29 A input limit. Valid range is 1.1 k–8 k; below
      1.1 k does not mean more current, it means undefined.
- [ ] `TS` → 10 kΩ NTC in the pack, **or a fixed 10 kΩ to VSS if the pack has
      none.** Not optional, not floatable.
- [ ] `/CHG`, `/PGOOD` → J4 LEDs, 1 k each **from the OUT rail** so they work
      with the Seed off. This is what satisfies P-2.
- [ ] `/CHG`, `/PGOOD` → also into the A11 encoder: **four 10 k 0.1% (C374544,
      in stock)** — pull-up **to 3V3**, 10 k on `/CHG`, 2×10 k series on
      `/PGOOD`, then 1 k / 10 nF to the pin. Pull-up on 3V3 and not OUT, so it
      draws nothing while off.
- [ ] Boost `FB` divider **348 k / 47.5 k for 5.0 V**. Not 5.2 V — see
      [values.md](values.md), it leaves 109 mV to the OVP minimum.
- [ ] Inductor **C354578** — 1 µH, 4.2 A Isat against a 1.51 A worst-case peak
      at 30% derating. Working in [sourcing.md](sourcing.md).
- [ ] `EN` 100 k pulldown; latch switch asserts EN from the OUT rail.
- [ ] Ferrite + 100 µF between boost output and everything downstream.
- [ ] Switch lamp from the 5 V rail through a **0 Ω 0603** link.

## Panel I/O sheet

- [ ] J5 wiper networks **1 kΩ / 100 nF**, not 220 Ω / 10 nF — the corner has to
      sit below the control rate, and a pot's own source impedance is part of
      the calculation.
- [ ] J11 100 Ω series on each of D0–D6.
- [ ] RGB **common anode to the 5 V rail**, GPIOs sinking. Series resistors
      **per channel from the chosen capsule's Vf** — a common value across all
      three is what breaks it.
- [ ] Comms port A: **both** footprints — 4-pin JST-SH on Qwiic pinout, and
      6-pin JST-PH module port. One populated.
- [ ] Comms port B on the same 6-pin module-port pinout.
- [ ] J16 expansion 2×4: 5 V, 3V3, GND, GND, D8, D9, D10, D30.
- [ ] Every DNP part marked DNP **in the schematic**, so the BOM and CPL inherit
      it rather than needing a manual pass.

## Audio sheet

- [ ] Output coupling, Pod-style.
- [ ] Input network on **every** board, DNP where unused.
- [ ] Electret bias, carbon bias and dynamic paths all footprinted; populate
      after measuring the capsule.
- [ ] **Mic bias return brought out to a two-position footprint** — link to
      ground, or wire to the hook switch's second pole so the current only flows
      off-hook.
- [ ] Earpiece fed from the **headphone** output through an attenuator, never
      the line output.

## Before DRC

- [ ] ERC clean, and read the warnings rather than suppressing them.
- [ ] Every net named; no auto-generated `Net-(U1-Pad3)` on anything that
      matters.
- [ ] BOM exported and checked against [values.md](values.md).
- [ ] **Re-run `python3 tools/gen_pinmap.py --check`.** If the map moved during
      capture, either the schematic is wrong or `pins.yaml` needed an ADR.

## Layout, when it comes

Frozen with the board, from the platform spec:

1. Zones — charger and barrel on one edge, boost in the corner beyond it, Seed
   centre, audio jacks on the opposite edge. Analogue IDC by the Seed's
   analogue row, digital IDC by its digital row.
2. **One unbroken ground plane.** No split AGND/DGND. Control noise by
   placement, not by cutting the return path.
3. Boost switching loop `VIN`/`L`/`SW`/`COUT` as small as possible.
4. No switcher traces under or parallel to audio nets or the analogue bus.
5. Enclosure bonds to ground at **one point**, at or near the audio jacks.
6. **QFN-16-EP exposed pad** — thermal via array, segmented paste apertures, not
   one large opening. That pad carries charge current.
7. Route the RGB lines away from the analogue bus; status changes are edges too.