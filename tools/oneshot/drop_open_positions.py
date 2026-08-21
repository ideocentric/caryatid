#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR 0010 — delete the four divider legs whose value is `open`.

    python3 tools/oneshot/drop_open_positions.py --apply

AN `open` POSITION CANNOT BE POPULATED, SO IT CANNOT SATISFY THE RULE
--------------------------------------------------------------------
The other twelve DNP symbols are parts awaiting a decision; clearing `dnp`
assembles them. These four are different. `open` is not a value a supplier can
ship -- the position exists precisely so that nothing is fitted -- so "no DNP
outside BT1" leaves exactly two options, delete or invent a value, and inventing
one would be four placements per board bought to satisfy a rule.

    R48  OUT_L_J -> GND    line-out shunt, left
    R50  OUT_R_J -> GND    line-out shunt, right
    R64  BYPASS_L -> GND   mic pad shunt, left
    R66  AUDIO_IN_R -> GND mic pad shunt, right

WHAT IS LOST, AND WHY IT IS ALREADY COVERED ELSEWHERE
-----------------------------------------------------
R48/R50 were the shunt arm of the line-out divider, so that either arm could
become a link once the earpiece was measured. The series arm survives: R47/R49
at 1k are fitted, and they are the attenuator audio.md actually argues for --
1k in series with a 150R earpiece is both the impedance fix and the ~13%
attenuation. The shunt was flexibility, not function.

R64/R66 were the carbon pad. The WM8731 line PGA reaches -34.5 dB (PD Rev 4.0,
Table 3, LINVOL/RINVOL at 00000), which is more attenuation than a resistor pad
would have been asked for, and it is adjustable at run time rather than fixed by
a soldering iron -- the same argument ADR 0009 made about the capsule.

NOTE R66 SITS ON THE WRONG NODE ANYWAY. R64 taps BYPASS_L, ahead of JP2, so the
pad stays in the bypass path. R66 taps AUDIO_IN_R, which is downstream of where
JP5 lands, so it would have padded the op-amp output too. Keeping the right pad
would have meant moving it first.

ONE-SHOT. Refuses to run twice: it stops if R48 is already gone.

EACH POSITION IS FIVE OBJECTS, and the geometry is uniform across all four --
confirmed, not assumed. For a resistor at (x, y):

    symbol R..      (x, y)              the part
    symbol GND      (x, y + 8.89)       power symbol on pin 2
    wire            (x, y - 3.81) -> (x, y - 8.89)
    wire            (x, y + 3.81) -> (x, y + 8.89)
    label           (x, y - 8.89)       the net it taps

VERIFY AFTER RUNNING: ERC clean, and the netlist must lose exactly four nodes
and no nets. OUT_L_J, OUT_R_J and BYPASS_L each keep two nodes; AUDIO_IN_R keeps
its global.
"""
import sys, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb",
                                    "audio.kicad_sch"))

# ref, x, y, the label on pin 1
DROP = [
    ("R48", 139.70, 54.61, "OUT_L_J"),
    ("R50", 139.70, 105.41, "OUT_R_J"),
    ("R64", 439.42, 209.55, "BYPASS_L"),
    ("R66", 439.42, 359.41, "AUDIO_IN_R"),
]


def near(a, b, tol=0.005):
    """Coordinates are compared as NUMBERS, never as text.

    KiCad writes 200.66000000000003 where the arithmetic here gives 200.66, and
    a textual match silently finds nothing -- which on a delete script means it
    stops rather than removing the wrong object, but it still stops.
    """
    return abs(float(a) - float(b)) < tol


def sexp(t, i):
    """The complete s-expression starting at t[i] == '('."""
    d, j = 0, i
    while True:
        if t[j] == "(":
            d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0:
                return t[i:j + 1]
        j += 1


def cut(t, start, blk, what, n):
    """Remove blk at start, taking the leading tab and trailing newline."""
    s = start
    while s > 0 and t[s - 1] == "\t":
        s -= 1
    e = start + len(blk)
    while e < len(t) and t[e] == "\n":
        e += 1
    print(f"    - {what}")
    return t[:s] + t[e:], n + 1


def main():
    t = open(SCH).read()
    if '"R48"' not in t:
        sys.exit("  R48 already gone -- this edit is already applied. Stopping.")

    n = 0
    for ref, x, y, netname in DROP:
        print(f"  {ref} at ({x}, {y}) tapping {netname}")

        # the resistor itself, matched on reference AND position
        def find_symbol(test, what):
            for m in re.finditer(r'\n\t\(symbol\n', t):
                blk = sexp(t, m.start() + 1)
                at = re.search(r'\(at ([-\d.]+) ([-\d.]+) \d+\)', blk)
                if at and test(blk, at):
                    return m.start() + 1, blk
            sys.exit(f"  FAILED to find {what}")

        s, blk = find_symbol(
            lambda b, at: re.search(r'\(property "Reference" "' + ref + r'"', b)
            and near(at.group(1), x) and near(at.group(2), y),
            f"symbol {ref} at ({x}, {y})")
        t, n = cut(t, s, blk, f"symbol {ref}", n)

        # the GND power symbol on pin 2
        s, blk = find_symbol(
            lambda b, at: '(lib_id "power:GND")' in b
            and near(at.group(1), x) and near(at.group(2), y + 8.89),
            f"the GND symbol at ({x}, {y + 8.89})")
        t, n = cut(t, s, blk, f"GND at ({x}, {y + 8.89})", n)

        # the two pin stubs
        for y1, y2 in ((y - 3.81, y - 8.89), (y + 3.81, y + 8.89)):
            hit = None
            for m in re.finditer(r'\(wire\n\t\t\(pts\n\t\t\t\(xy ([-\d.]+) ([-\d.]+)\)'
                                 r' \(xy ([-\d.]+) ([-\d.]+)\)', t):
                a, b, c, d_ = m.groups()
                if near(a, x) and near(b, y1) and near(c, x) and near(d_, y2):
                    hit = m.start()
                    break
            if hit is None:
                sys.exit(f"  FAILED to find the wire {x},{y1} -> {x},{y2}")
            t, n = cut(t, hit, sexp(t, hit), f"wire {y1} -> {y2}", n)

        # the label on pin 1
        hit = None
        for m in re.finditer(r'\((?:label|global_label) "' + netname
                             + r'"[\s\S]{0,120}?\(at ([-\d.]+) ([-\d.]+) \d+\)', t):
            if near(m.group(1), x) and near(m.group(2), y - 8.89):
                hit = m.start()
                break
        if hit is None:
            sys.exit(f"  FAILED to find the {netname} label at ({x}, {y - 8.89})")
        t, n = cut(t, hit, sexp(t, hit), f"label {netname}", n)

    print(f"  removed {n} objects across {len(DROP)} positions")
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"  paren balance {d}")
    if d != 0:
        sys.exit("  UNBALANCED -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(SCH, "w").write(t)
    print(f"  wrote {SCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())