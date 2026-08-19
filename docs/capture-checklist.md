# Schematic capture checklist

Ordered so the frozen pin map gets **enforced** rather than re-derived. Work
down it; do not skip ahead to the fun part.

## Before opening KiCad

- [ ] **Confirm the licence answer is still "draw from the datasheets."**
      [ADR 0006](decisions/0006-licensing-is-open.md). Once a schematic derives
      from someone else's source file it cannot be un-derived. Nobody opens an
      Adafruit schematic during this work.
- [ ] **Measure the handset capsule** — DC resistance across it decides whether
      the input network gets a preamp or a pad. [audio.md](audio.md). **It also
      sets the largest unresolved term in the 5 V budget**: R52/R54 bias at
      220 Ω each, so 23–41 mA for the pair depending where the capsule sits —
      up to 16% of the typical rail load. See the line-item table in
      [values.md](values.md).
- [x] ~~Verify D26 / D27 / D29 are 5 V tolerant.~~ **Done** — all three are
      `FT` per Table 7 of `DS12556`. Common anode to 5 V with the GPIOs sinking
      is the scheme; see [values.md](values.md) for the absolute-maximum
      condition and why the pin never actually sees 5 V here.
- [x] ~~Check the bq24074's JLC PCBA type.~~ **Done** — Economic **and**
      Standard, same as the boost. The Economic assembly split holds. Library
      type is unpublished for both; assume Extended and a ~$3 setup fee each,
      which JLC prices when the BOM goes up.
- [x] ~~Measure the RGB forward voltages and confirm common anode.~~ **Done** —
      common anode confirmed, Vf 2.0–2.2 V red and 3.0–3.2 V green/blue. Start
      at 510 Ω red, 300 Ω green and blue, then **tune green down by eye** —
      equal current is not equal brightness.
- [ ] **Measure the switch bezel diameter** (Ø12 / 16 / 19). It is the only
      mechanical number still missing — the DC jack, audio jacks and LED bezel
      are specified in [sourcing.md](sourcing.md), and the lamp's electrical
      side was settled by it being a 3–9 V variant.
- [ ] **No jack footprints on the board.** Every panel part is panel-mounted and
      arrives on a JST — J1 for DC in, J17 and J18 for audio. See
      [connectors.md](connectors.md).

- [ ] **Reuse the absonus footprints** listed in [sourcing.md](sourcing.md) —
      they are drawn and fabricated already. Check pin-1 orientation and JST
      polarity against *this* schematic; proven to fabricate is not proven
      correct here.

## Sheet structure

Hierarchical, so the power section stays a reusable block for a future board:

- [x] `power.kicad_sch` — charger, boost, latch, hardware charge LEDs
- [x] `seed.kicad_sch` — Seed sockets, battery gauge, charge-status code
- [x] `audio.kicad_sch` — jacks, coupling, mic bias and preamp/pad options
- [x] `panel-io.kicad_sch` — analogue bus, digital bus, switches, comms ports

## Enforcing the pin map

**This is the part that matters.** `docs/pins.yaml` is the source of truth, and
the schematic is a *consumer* of it, not a second opinion.

- [x] Label every Seed net with the **pin name from `pins.yaml`** — `A7`, `D11`
      — not with what the net does on one instrument. `D11` is not `SCL`; it is
      `D11`, and I2C is one thing it can be.
- [x] **Cross-check the finished schematic against `pinmap.md` pin by pin.** By
      script if you can face writing one, by eye if not, but do it as a
      distinct pass rather than while drawing.
- [x] **`D8` is the only free SPI1 clock.** If anything ends up on it that is
      not the expansion header, stop.
- [x] **Hook switch on `D7`, never `D13`/`D14`.** Those two are comms port B and
      USART1 needs both.

## Power sheet

**Captured.** `power.kicad_sch` holds all 27 components and 19 nets, ERC is
clean, and the exported netlist was diffed node-by-node against
[power-sheet.md](power-sheet.md) — every net matches. The boxes ticked below are
the ones that diff proves. The unticked ones are layout or silkscreen work, or
belong to another sheet.

- [x] **`EN2` to `VOUT`, never to `VIN_DC`.** EN1/EN2/CE are 7 V absolute max
      and VIH is valid only to 6 V; the barrel input goes to 9 V. This is the
      one that destroys a part.
- [x] **`ILIM` must be populated** — leaving it open disables all charging.
- [x] **`ITERM` no-connect flag**, deliberately floating for 10% termination.
- [x] **Charge LED anodes on `VOUT`, not `+5V`** — they must work with the
      boost off, which is the whole point of them.
- [x] C1 rated **25 V**: it sits on the raw barrel input.

- [ ] Barrel jack → SS34 → bq24074 `IN`. **5–9 V, never 12 V** — silkscreen it.
- [x] `RISET` **887 Ω, 1%** — the 1% is a datasheet requirement, not a
      preference; the part short-tests this resistor.
- [x] `RILIM` **1.2 kΩ** → 1.29 A input limit. Valid range is 1.1 k–8 k; below
      1.1 k does not mean more current, it means undefined.
- [x] `TS` → 10 kΩ NTC in the pack, **or a fixed 10 kΩ to VSS if the pack has
      none.** Not optional, not floatable.
- [x] `/CHG`, `/PGOOD` → J4 LEDs, 1 k each **from the OUT rail** so they work
      with the Seed off. This is what satisfies P-2.
- [x] `/CHG`, `/PGOOD` → also into the A11 encoder: **four 10 k 0.1% (C374544,
      in stock)** — pull-up **to 3V3**, 10 k on `/CHG`, 2×10 k series on
      `/PGOOD`, then 1 k / 10 nF to the pin. Pull-up on 3V3 and not OUT, so it
      draws nothing while off.
- [x] Boost `FB` divider **348 k / 47.5 k for 5.0 V**. Not 5.2 V — see
      [values.md](values.md), it leaves 109 mV to the OVP minimum.
- [ ] Inductor **C354578** — 1 µH, 4.2 A Isat against a 1.51 A worst-case peak
      at 30% derating. Working in [sourcing.md](sourcing.md).
- [x] `EN` 100 k pulldown; latch switch asserts EN from the OUT rail.
- [x] Ferrite + 100 µF between boost output and everything downstream.
- [x] Switch lamp from the 5 V rail through a **0 Ω 0603** link.

## Seed sheet

**Captured.** `seed.kicad_sch` holds both sockets and the two measurement
networks. ERC has no errors; the 33 warnings are all `global_label_dangling`,
one per Seed pin that leaves for panel-io or audio — sheets not yet captured.
That count is a checksum: 15 `D0`–`D14`, 10 `A0`–`A9`, 4 RGB/expansion, 4 audio.
It should fall to zero as those sheets land, and any *other* dangling label is a
mistake.

The cross-check against the frozen map was run as its own pass, by script:
**all 31 physical pins in `pins.yaml` land on a net named after the pin.**

- [x] **Name every Seed net after its pin** — `D0`, `A7`. That is what turns
      the cross-check against `pinmap.md` into a diff.
- [x] **`AGND` (pin 20) ties to `GND`.** One plane; no split.
- [x] `3v3A` (21) and `3v3D` (38) stay separate — supplies, not returns.
- [x] Battery gauge on A10: 100 k / 100 k, then 1 k / 10 nF at the pin.
- [x] A11 encoder: four 10 k 0.1%, 20 k leg made from two in series.
- [x] **No no-connects on this sheet.** All forty pins are used; if ERC finds
      one, something is missing.
- [x] **Two socket designators, `A1` and `A2`**, one per 1×20 strip. absonus
      used a single designator and the BOM asked for one socket where the board
      needs two. Using both symbols is what makes the schematic carry the
      quantity — placing one twice would put the same designator on both.
- [x] ~~Draw the Seed orientation back in as silkscreen~~ — outline, pin-1 dot,
      square pads at the USB end of both rows, and the `USB` legend are **inside
      the two footprints**, so they travel with the sockets. Per-pin labels were
      drawn and then dropped: see [seed-sheet.md](seed-sheet.md).
- [ ] **Place `A1` and `A2` exactly 15.24 mm apart** at layout. The outline and
      USB tab are split across the two footprints and only close up at that
      spacing — a broken outline on the board render means the spacing is wrong.

## Panel I/O sheet

**Captured.** `panel-io.kicad_sch` holds 59 placements across 46 components. No
custom symbols — the 74HC14 and every connector are stock KiCad.

ERC has no errors, and the dangling-global count has fallen **33 → 4**: the only
labels still unresolved are `AUDIO_IN_L/R` and `AUDIO_OUT_L/R`, waiting on the
audio sheet. That was the predicted number, and it landing exactly is the check.

The pin-map enforcement pass was run by script against `pins.yaml`, traversing
series resistors and the debouncer rather than demanding a direct connection:
**all 29 pins that declare a connector reach it**, and A10/A11 correctly reach
none because they are on-board measurements.

- [x] **A4 gets 10 kΩ, A5 gets 3 kΩ.** The spec had these transposed; the
      fabricated absonus board is the authority. FSR 10 k, soft pot 3 k.
- [x] **Hook switch on SW3 / J8 / `D7`.** Never SW1 or SW2 — those are comms
      port B and USART1 needs both pins.
- [ ] 74HC14 per channel: 10 kΩ pull-up, 10 kΩ series, C to ground. **C is a
      population choice** — 220 nF panel, **1 µF for a hook lever**. 100 nF is
      below typical bounce.
- [ ] **Tie unused 74HC14 inputs (9, 11, 13) to `GND`.** Floating CMOS inputs
      oscillate.
- [ ] 100 nF decoupling on the 74HC14.
- [ ] **The output is inverted — leave it that way.** An unplugged cable then
      reads as switch-open, which for loa is on-hook and silent. See
      [ADR 0007](decisions/0007-rc-and-schmitt-instead-of-the-ls18-p.md).
- [ ] J5 wipers **1 kΩ / 100 nF**, not 220 Ω / 10 nF.
- [ ] J11 **100 Ω series** on each of D0–D6.
- [ ] RGB **510 Ω red, 300 Ω green and blue**, anode on `+5V`.
- [ ] I2C pull-ups 4.7 kΩ **DNP** — a UART on the same pins does not want them.
- [ ] Every unpopulated part marked **DNP in the schematic**.

## Audio sheet

Every provision is in [audio.md](audio.md). The whole sheet is DNP-heavy by
design — it exists so the capsule question can be answered after the boards
arrive rather than before the gerbers go out.

- [ ] Output coupling, Pod-style, to **J17** — not to a board-mounted jack.
- [ ] Earpiece attenuator: a series resistor does both jobs, raising the load
      impedance as it drops the level. **No headphone amp on this board.**
- [ ] Input network on **every** board, DNP where unused.
- [ ] **U4 MCP6002 gain stage, DNP**, powered from `3V3A`, both channels laid
      out. Carbon bypasses it, electret takes ~×100, dynamic takes maximum.
- [ ] **Mid-rail bias network** — 100 k / 100 k / 10 µF. A single-supply stage
      without it clips half the waveform.
- [ ] **`C_g` in series with `R_g`.** Without it, DC gain equals AC gain and the
      bias pedestal is amplified into the rail.
- [ ] **Bypass as a two-resistor divider**, not a 0 Ω link — a carbon capsule may
      need padding down rather than passing through.
- [ ] Electret bias, carbon bias and dynamic paths all footprinted; populate
      after measuring the capsule.
- [ ] **Mic bias return to a two-position footprint** — link to ground, or out to
      the hook switch's second pole so current only flows off-hook.
- [ ] Earpiece from the **headphone** output through an attenuator, never the
      line output.
- [ ] Confirm the WM8731 line PGA's gain range from the codec datasheet — the
      dynamic case relies on ~+12 dB from it.

## Before DRC

- [ ] ERC clean, and read the warnings rather than suppressing them.
- [ ] Every net named; no auto-generated `Net-(U1-Pad3)` on anything that
      matters.
- [ ] BOM exported and checked against [values.md](values.md).
- [ ] **Re-run `python3 tools/gen_pinmap.py --check`.** If the map moved during
      capture, either the schematic is wrong or `pins.yaml` needed an ADR.

## Board level — none of this belongs to a sheet

- [x] **Two layers, 150 × 90 mm.** All growth is on the long axis, where the
      conservative BUD rectangle leaves 15 mm spare; the 90 mm axis is unchanged
      because it is the one proven to fit. See
      [ADR 0008](decisions/0008-board-outline-and-layer-count.md).
- [x] ~~SMD on one face, holder and through-hole connectors on the other.~~
      **Everything is on the front**; the back is bare copper. The enclosure is
      shallow, so the standoff has to be short, and C7 at 5.4 mm cannot hang
      under it. Single-sided SMT is also the cheaper assembly.
- [x] **Corners rounded, 3 mm radius.** Nothing electrical or mechanical forced
      a value — see ADR 0008 for what was checked and ruled out. Re-run
      `tools/round_corners.py` to change it; refill the zones afterwards.
- [x] **Four M3 holes**, pattern chosen once the outline settles. **Unaffected by
      the corner radius** — they sit 5 mm in from both edges and keep their full
      5 mm to the straight edge, so the ±40 / ±70 CU-477 drill pattern below
      still stands.
- [ ] **Drill the CU-477 floor** to the **140 × 80 mm** pattern — but **not
      centred on the floor.** Set it out from the walls, not from the middle:
      **10 mm from the left (screw-column) end**, **28 mm from the right
      (power-button) end**, **15 mm from each long wall.** The board is
      deliberately offset **left**, for two reasons that agree: the latching
      power button is long and needs the right-hand space, and the device is
      held in the **left hand**, so the board's mass sits over the supporting
      hand instead of cantilevered right where the same weight reads as heavier.
      See [the enclosure record](../discovery/findings/bud-cu477-interior.yaml).
      Centring the pattern puts the board 9 mm into the button's space **and**
      throws the balance right.
      The bottom ships blank; all 108 M3 holes in BUD's STEP are in the walls
      and flanges. See [sourcing.md](sourcing.md). absonus's 1.6″ × 3.6″ pattern
      is deliberately **not** inherited.
- [ ] **Confirm the power switch's plan position** before drilling anything. The
      12 mm LED latching switch descends **23 mm** into a 34 mm interior, leaving
      11 mm beneath it against a 26.91 mm stack. It must land in the reserved
      28 mm strip with no board under it. This is inference from the mounting
      convention, not a stated fact — **check it.**
- [x] ~~On-board 18650 holder, and keep J2.~~ **J2 is removed.** The cell reaches
      the board only through BT1, so there is no "one or the other" to silkscreen
      and no way to present a reversed cell to the charger.
- [x] ~~Holder must accept a **protected** cell at ~69 mm~~ **Settled** — BT1 is
      MPD **BH-18650-PC**, `C5339083`, footprint
      `Battery:BatteryHolder_MPD_BH-18650-PC`. The drawing states it is designed
      for protected cells. Economic assembly, same tier as the charger.
- [ ] **Bolt BT1 down**, don't rely on the two solder tabs. Ø3.2 mm holes at
      55.61 mm — put the mounting holes in the board outline.
- [x] ~~Confirm the outline clears the BUD CU-477.~~ **Measured in hand
      2026-08-18: 178 × 110 mm floor, 34.0 mm interior height.** 150 × 90 has
      28 mm of long-axis slack and 20 mm of short; headroom is 7.09 mm at the
      26.91 mm stack. The 95.2 × 165.1 working rectangle is retired — it
      under-read the real box by 12.9 and 14.8 mm. See
      [the record](../discovery/findings/bud-cu477-interior.yaml) and
      [sourcing.md](sourcing.md).
- [x] ~~Record the telephone shell's measured internal floor.~~ **6″ × 4″ usable
      — 152.4 × 101.6 mm — and that figure already holds ≥ 0.25″ (6.35 mm)
      clearance on every side.** 150 × 90 lands inside it with 1.2 mm per end and
      5.8 mm per side spare, so **~7.5 mm per end and ~12.1 mm per side** of true
      clearance. External is 129.5 × 221 mm. See
      [loa 12-phone-build.md](../../loa/docs/design/12-phone-build.md).
- [x] ~~Standoffs are 7 mm minimum~~ — **4 mm, as built.** The back face is empty,
      so **2 mm** is all the electrical clearance needs; 4 mm is the mechanical
      choice and there is headroom for it. Do not read the 2 mm as a build spec.
      Stack is **26.91 mm** — 4 + 1.6 PCB + 21.31 BT1.
- [x] ~~Check height, not just floor area.~~ **Both enclosures clear the 26.91 mm
      stack** (4 mm standoff + 1.6 mm PCB + **21.31 mm** BH-18650-PC — **the
      holder sets the height, not the Seed**, which is only 10.5 mm).

      | | interior height | headroom |
      | --- | --- | --- |
      | telephone shell | > 40 mm | > 13 mm |
      | **BUD CU-477** | **34.14 mm** | **7.23 mm** |

      The BUD is the binding case. Its interior height is **derived from the STEP
      model**, not measured: external is 38.10 mm (1.500″) and both the base and
      the cover independently give a **1.98 mm wall**, which reconciles exactly
      (38.10 − 2 × 1.98 = 34.14). Two solids agreeing is good corroboration but it
      is still inference from the model — **confirm with calipers before the cell
      is committed to the board.**

      One reservation: a plane sits **1.60 mm proud of the base floor**. If the
      standoffs land on that rather than on the floor itself, headroom is
      **5.63 mm**. Still adequate; check which surface they seat on.

      *(Was written as a 19 mm holder giving ~26.6 mm before the part was chosen,
      then ~30 mm, then ~25 mm at a 2 mm standoff.)*
- [ ] **Test points** on `VBAT`, `VOUT`, `+5V`, `+3V3`, `+3V3A` and `GND`.
- [x] ~~**Fiducials** — three top-side; confirm JLC's requirement.~~ **Done.**
      FID1 (58.25, 40.25), FID2 (191.75, 41.00), FID3 (69.25, 108.75) —
      `Fiducial_1mm_Mask2mm`, 1 mm bare copper in a 2 mm mask opening, no net.
      An **L, not a symmetric trio**: rotated 180° none of the three lands on
      another, so orientation is unambiguous. Separations 69/134/140 mm.
      Board-only footprints like the mounting holes, so they carry no schematic
      symbol and no BOM or CPL line.
- [ ] **J14** carries the mic bias return to the hook switch's second pole. It is
      the number the soft-latch vacated, not a gap.
- [ ] **Silkscreen the pin function beside every connector**, and pin 1 on all of
      them. Assembled once, cabled many times.
- [x] ~~Battery polarity marked at J2.~~ Moot: J2 is gone, and a soldered holder
      cannot be wired backwards.
- [ ] Confirm the 2×5 IDC parts are **shrouded/keyed** box headers, not bare pin
      headers. Ribbon polarity depends on it.

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
6. **QFN-16-EP exposed pad** — thermal vias (**two**, mask-tented on both faces;
   four would leave 10% of the EP solderable), segmented paste apertures, not
   one large opening. That pad carries charge current.
7. Route the RGB lines away from the analogue bus; status changes are edges too.
8. **Place `A1` and `A2` exactly 15.24 mm apart.** The Seed outline, pin names
   and `USB` legend live *inside* the two socket footprints and travel with
   them, so there are no free graphics to fall out of step — but the outline and
   the USB tab are split on the centreline and only close up at that spacing. A
   broken outline on the board render means the spacing is wrong.