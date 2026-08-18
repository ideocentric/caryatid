# Power sheet

Every connection on `hardware/pcb/power.kicad_sch`, so capture is transcription
rather than design. Values are derived in [values.md](values.md), part numbers in
[sourcing.md](sourcing.md).

Pin numbers are from `SLUS810N` Table 7-1, **'74 column** — the variants differ,
and pin 15 is `ITERM` on this one where it is `TD` or `SYSOFF` on others.

## Three things the datasheet says that are easy to get wrong

**`EN1`, `EN2` and `CE` are 7 V absolute maximum, with VIH valid only to 6 V.**
The barrel input is specified 5–9 V. **Tying `EN2` to the input rail — the
obvious way to select ILIM mode — destroys the pin on a 9 V adapter.** Tie it to
`VOUT` instead: present whenever input or battery is, and never above ~4.5 V.

**Leaving `ILIM` unconnected disables all charging.** It is not a
default-to-maximum pin.

**`ITERM` is deliberately left unconnected** on the '74 to select the default 10%
termination. Put a no-connect flag on it so ERC knows it is intentional.

Two more numbers worth having: `IN` is rated to **28 V** absolute, but the '74's
input over-voltage protection trips at **10.2–10.8 V** — which is where "5–9 V,
never 12 V" comes from. And `CHG`/`PGOOD` sink at most **15 mA**.

## Components

| Ref | Part | Value | LCSC |
| --- | --- | --- | --- |
| J1 | JST-XH 2 | DC in, from the panel barrel jack | C158012 |
| D1 | Schottky | SS34, SMA | C8678 |
| U1 | Charger | BQ24074RGT, QFN-16-EP | C54313 |
| U2 | Boost | TPS61023DRL, SOT-563 | C919459 |
| L1 | Inductor | 1 µH, 4.2 A Isat | C354578 |
| FB1 | Ferrite bead | **rated ≥ 1 A** | — |
| BT1 | 18650 holder | MPD **BH-18650-PC** — rated for **protected** cells | **C5339083** |
| J3 | Latch switch | JST-XH 4 | C144395 |
| J4 | Charge LEDs | JST-XH 4 | C144395 |
| R1 | TS | 10 kΩ | C15401 |
| R2 | ILIM | 1.2 kΩ | — |
| R3 | ISET | **887 Ω 1%** | — |
| R4 | TMR | 46.4 kΩ | — |
| R5 | Lamp link | **0 Ω**, 0603 | — |
| R6 | EN pulldown | 100 kΩ | — |
| R7 | FB upper | **348 kΩ 1%** | — |
| R8 | FB lower | **47.5 kΩ 1%** | — |
| R9, R10 | Charge LED | 1 kΩ | — |
| C1 | VIN_DC bulk | 10 µF 0805, ≥ 25 V | — |
| C2 | BAT | 10 µF 0805 | — |
| C3 | VOUT | 10 µF 0805 | — |
| C4, C5 | Boost input | 10 µF 0805 | — |
| C6 | Boost output | 22 µF 0805 | — |
| C7 | After the ferrite | 100 µF, `CP_Elec_6.3x5.4` | **not sourced** — see below |

C1 needs a **25 V** rating: it sits on the raw barrel input, which can be 9 V and
is only protected from 28 V by the OVP.

> **C7 was listed here as `C3337`. That was wrong and is corrected.** The
> absonus BOM as actually ordered (`local/reference/bom.xls`) shows C3337 is a
> **220 µF part in `CP_Elec_5x5.4`**, matching [sourcing.md](sourcing.md). C7 is
> 100 µF in `CP_Elec_6.3x5.4` — a different value in a different body, so the
> part does not fit and would not be the right capacitance if it did. C7 has no
> part number yet; it is decision D in sourcing.md.

## Nets

### Input

| From | To |
| --- | --- |
| J1.1 | D1 anode — **centre pin of the panel jack** |
| J1.2 | `GND` — sleeve |
| D1 cathode | `VIN_DC` |
| `VIN_DC` | C1 → `GND` |
| `VIN_DC` | U1.13 `IN` |

D1 in series gives reverse-polarity protection at the cost of ~0.4 V. The charger
needs 4.35 V minimum at `IN`, so a 5 V adapter still has margin.

### Charger U1

| Pin | Net | Note |
| --- | --- | --- |
| 13 `IN` | `VIN_DC` | |
| 8 `VSS` | `GND` | |
| 17 `EP` | `GND` | thermal pad — via array, it carries charge current |
| 2, 3 `BAT` | `VBAT` | both pins, not one |
| 10, 11 `OUT` | `VOUT` | both pins |
| 1 `TS` | R1 10 kΩ → `GND` | **fixed resistor** — the pack has no thermistor |
| 4 `CE` | `GND` | active low; enabled. Do not float. |
| 6 `EN1` | `GND` | |
| 5 `EN2` | **`VOUT`** | selects ILIM mode. **Not `VIN_DC` — 7 V abs max.** |
| 12 `ILIM` | R2 1.2 kΩ → `GND` | 1.29 A input limit |
| 16 `ISET` | R3 887 Ω 1% → `GND` | 1 A charge. 1% is required, not preferred. |
| 14 `TMR` | R4 46.4 kΩ → `GND` | 6.25 h safety timer |
| 15 `ITERM` | **no connect** | default 10% termination |
| 7 `PGOOD` | `~{PGOOD}` | open drain |
| 9 `CHG` | `~{CHG}` | open drain |

`EN2 = 1, EN1 = 0` is Table 7-2's "set by an external resistor from ILIM to VSS".

### Battery reverse polarity — understood, not protected

**A cell connected backwards destroys the charger.** `BAT` is rated −0.3 V to
5 V, and a reversed 18650 puts −4.2 V on it.

There is no protection, deliberately: a series diode wastes 0.3 V and permanent
power on every discharge, and a P-FET is parts and board area for a fault the
mechanics already prevent.

**BT1 removes the risk rather than mitigating it** — a soldered holder cannot be
wired backwards, which is the main reason it is on the board at all.

**With J2 gone there is no residual exposure at all.** The only way to present a
reversed cell used to be a hand-crimped loom on J2, where the JST-XH is keyed but
the crimp can still be wrong. There is now no connector on the board that reaches
`VBAT`, so the unprotected charger input cannot be miswired.

### Battery and output

| From | To |
| --- | --- |
| BT1 + | `VBAT` |
| BT1 − | `GND` |
| `VBAT` | C2 → `GND` |
| `VOUT` | C3 → `GND` |

**The cell reaches the board only through BT1.** J2, a JST-XH for a remote pack,
was carried until the board was laid out and then removed: nothing on the
platform wanted it, and it was the last path by which a reversed cell could reach
an unprotected charger input.

### Latch switch J3

| Pin | Net |
| --- | --- |
| J3.1 | `VOUT` — switch common |
| J3.2 | `EN_SW` — switch return |
| J3.3 | `+5V` through R5 (0 Ω) — lamp anode |
| J3.4 | `GND` — lamp cathode |
| — | R6 100 kΩ from `EN_SW` to `GND` |

The lamp runs from the **switched** 5 V rail, so it follows the boost and needs
no firmware. R5 is a 0 Ω link because the 3–9 V lamp limits its own current;
the footprint stays so a different switch can drop in.

### Boost U2

| Pin | Net |
| --- | --- |
| 3 `VIN` | `VOUT` |
| 4 `GND` | `GND` |
| 2 `EN` | `EN_SW` |
| 5 `SW` | L1, other end to `VOUT` |
| 6 `VOUT` | `+5V_RAW` |
| — | C4, C5 from `VOUT` to `GND` — close to pin 3 |
| — | C6 from `+5V_RAW` to `GND` |
| — | R7 348 kΩ `+5V_RAW` → `FB`; R8 47.5 kΩ `FB` → `GND` |

**The inductor sits between the input rail and `SW`**, not in the output. The
`VIN`/L1/`SW`/C6 loop is the one to keep small in layout — 1 MHz switching and a
1.51 A worst-case peak.

R7/R8 set 5.0 V, not 5.2 V. See [values.md](values.md) — 5.2 V leaves 109 mV to
the OVP minimum.

### Output filter

| From | To |
| --- | --- |
| `+5V_RAW` | FB1 → `+5V` |
| `+5V` | C7 100 µF → `GND` |

`+5V` leaves the sheet as a power symbol: the Seed's VIN, the RGB anode, the
module ports and the switch lamp.

### Charge LEDs J4

| Pin | Net |
| --- | --- |
| J4.1 | `VOUT` — common anode, both LEDs |
| J4.2 | R9 1 kΩ → `~{CHG}` |
| J4.3 | R10 1 kΩ → `~{PGOOD}` |
| J4.4 | `GND` |

**Anodes on `VOUT`, not `+5V`.** `VOUT` is alive whenever a battery or an adapter
is, and the boost is not — which is the entire reason these LEDs exist. Powering
them from `+5V` would make them go dark exactly when they matter.

At 1 kΩ from ~4.2 V through a ~2 V LED that is 2.2 mA, comfortably inside the
15 mA the status pins can sink.

## With no latch switch fitted, the board does not power up

`R6` holds `EN` low, so the boost stays off until the switch pulls it high from
`VOUT`. That is correct — it is what makes the switch a real power switch — but
it means **a bare board on the bench is dead** until J3 is bridged.

Do not treat that as a fault. Bridge J3 pins 1–2, or fit a temporary link, and
say so in the bring-up notes.

## Leaving the sheet

Rails are power symbols and global by nature: `GND`, `+5V`, `VBAT`, `VOUT`,
`VIN_DC`.

**Name them exactly that.** The net classes in the project file assign by
pattern, so `VBAT` lands in HighCurrent at 1.2 mm while a net called `BAT+`
silently falls into Default at 0.25 mm.

Two labels go to the **seed** sheet, where the A11 encoder lives:

- `~{CHG}`
- `~{PGOOD}`

**They are captured as global labels, not hierarchical ones.** Hierarchical
labels need matching sheet pins on the root sheet, and a sheet pin that leads to
a sheet which has not been captured yet is an ERC error rather than a promise.
Global labels connect across sheets directly, which for four sheets and two
signals is the proportionate mechanism. If the sheets are ever made reusable,
this is the thing to revisit.

## Layout notes for this sheet

1. J1 and the charger on one edge, boost in the corner beyond it.
2. **Minimise the `VIN`/L1/`SW`/C6 loop area.** This is the only genuinely
   high-frequency thing on the board.
3. **Thermal vias under U1's exposed pad**, with segmented paste apertures. That
   pad is doing thermal work at 1 A of charge current, not just mechanical.
4. No switching traces under or parallel to the analogue bus or audio nets.
5. C4/C5 as close to U2 pin 3 as the layout allows; C6 close to pin 6.