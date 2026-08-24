#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lift JP6 and everything attached to it out of the title block.

    python3 tools/oneshot/move_jp6_clear_titleblock.py            # report
    python3 tools/oneshot/move_jp6_clear_titleblock.py --apply

THE DEFECT
----------
check_schematic.py found JP6 at (480.06, 391.16) on audio.kicad_sch, an A2
sheet. The title block occupies roughly the bottom-right 110 x 32 mm inside the
border, so anything past x 474 and y 378 lands on it. JP6's cluster spans y
379.16 to 393.70 and its pin labels print across "File: audio.kicad_sch".

WHY THIS IS NOT "MOVE ONE SYMBOL"
----------------------------------
**Schematic connectivity is positional.** A wire connects to a pin because its
endpoint sits ON the pin, not because anything records a relationship. Moving
the symbol alone would silently disconnect all three pins and change the
netlist, and the schematic would still look almost right.

So the whole cluster moves together, identified by exact coordinates:

    symbol JP6              (480.06, 391.16)
    Reference, Value        (486.06, 379.16) and (486.06, 382.16)
    3 labels                x 469.90, y 388.62 / 391.16 / 393.70
    3 wires, both ends      (469.90, y) to (474.98, y), same three y

The pins sit 5.08 mm left of the symbol origin, which is why the wires end at
474.98. Symbol and wires move by the same delta, so that stays true.

THE DISTANCE, AND WHY THIS ONE
-------------------------------
Up 22.86 mm, which is 9 x 2.54 and keeps everything on the grid it is already
on. JP6 lands at y 368.30 and its cluster spans 356.30 to 370.84:

    clears the title block edge at y 378 by 7.2 mm
    clears JP5's cluster, which ends near 343, by 13 mm

Moving it LEFT instead would clear the block just as well and would break the
column: JP1 to JP6 all sit at x 480.06, evenly spaced down the sheet, and that
column is the one piece of deliberate layout on this page.

VERIFIED BY NETLIST, NOT BY EYE. The tool exports the netlist before and after
and refuses to keep the edit unless they match. A visual check cannot see a pin
that came adrift by 2.54 mm.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb",
                                    "audio.kicad_sch"))
ROOT = os.path.join(os.path.dirname(SCH), "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

DY = -22.86          # up 9 x 2.54 mm

# Everything that must move, by exact current coordinate.
SYMBOL = (480.06, 391.16)
FIELDS = [(486.06, 379.16), (486.06, 382.16)]
LABEL_X = 469.90
WIRE_XS = (469.90, 474.98)
YS = (388.62, 391.16, 393.70)


def near(a, b, tol=0.005):
    return abs(a - b) < tol


def netlist(path, tag):
    out = f"/tmp/jp6-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    t = open(out).read()
    nets = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                         t, re.S):
        nodes = sorted(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
        nets[m.group(1)] = nodes
    return nets


def main():
    apply_ = "--apply" in sys.argv
    t = open(SCH).read()
    edits = 0

    def shift_at(block, x, y):
        """Rewrite the first (at x y ...) in block, shifting y by DY."""
        m = re.search(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", block)
        if not m:
            return block, False
        bx, by = float(m.group(1)), float(m.group(2))
        if not (near(bx, x) and near(by, y)):
            return block, False
        return (block[:m.start()] +
                f"(at {bx:g} {by + DY:g}{m.group(3)})" +
                block[m.end():]), True

    def sexp(s, i):
        d = 0
        for j in range(i, len(s)):
            if s[j] == "(":
                d += 1
            elif s[j] == ")":
                d -= 1
                if d == 0:
                    return s[i:j + 1]
        return s[i:]

    # collect first, write back to front, per docs/conventions.md rule 2
    todo = []

    for m in re.finditer(r"^\t\(symbol\b", t, re.M):
        blk = sexp(t, m.start() + 1)
        if "(lib_id " not in blk:
            continue
        if not re.search(r'\(property "Reference" "JP6"', blk):
            continue
        new = blk
        new, ok = shift_at(new, *SYMBOL)
        if not ok:
            sys.exit(f"  JP6 is not at {SYMBOL}; the sheet has changed. Stopping.")
        for fx, fy in FIELDS:
            for pm in re.finditer(r'\(property "', new):
                pb = sexp(new, pm.start())
                pnew, pok = shift_at(pb, fx, fy)
                if pok:
                    new = new[:pm.start()] + pnew + new[pm.start() + len(pb):]
                    break
        todo.append((m.start() + 1, blk, new, "symbol JP6 + its two fields"))

    for m in re.finditer(r'\((?:label|global_label|hierarchical_label) "', t):
        blk = sexp(t, m.start())
        for y in YS:
            new, ok = shift_at(blk, LABEL_X, y)
            if ok:
                nm = re.match(r'\(\w+ "([^"]*)"', blk).group(1)
                todo.append((m.start(), blk, new, f"label {nm}"))
                break

    for m in re.finditer(r"\(wire\b", t):
        blk = sexp(t, m.start())
        pts = re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", blk)
        if len(pts) != 2:
            continue
        (x1, y1), (x2, y2) = [(float(a), float(b)) for a, b in pts]
        if not (near(y1, y2) and any(near(y1, y) for y in YS)):
            continue
        if not ({round(x1, 2), round(x2, 2)} == {round(WIRE_XS[0], 2),
                                                 round(WIRE_XS[1], 2)}):
            continue
        new = blk
        for a, b in pts:
            new = new.replace(f"(xy {a} {b})",
                              f"(xy {a} {float(b) + DY:g})", 1)
        todo.append((m.start(), blk, new, f"wire at y {y1}"))

    print(f"  moving {len(todo)} elements by {DY:+.2f} mm in Y")
    for _, _, _, what in todo:
        print(f"      {what}")
    expect = 1 + len(YS) + len(YS)
    if len(todo) != expect:
        sys.exit(f"\n  expected {expect} elements (symbol + {len(YS)} labels + "
                 f"{len(YS)} wires), found {len(todo)}. Stopping.")

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist(SCH, "before")
    backup = SCH + ".bak"
    shutil.copy(SCH, backup)

    for start, old, new, _ in sorted(todo, key=lambda e: -e[0]):
        if t[start:start + len(old)] != old:
            sys.exit("  offset no longer holds what was measured -- not writing")
        t = t[:start] + new + t[start + len(old):]
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    open(SCH, "w").write(t)

    after = netlist(SCH, "after")
    if before != after:
        shutil.copy(backup, SCH)
        os.remove(backup)
        added = set(after) - set(before)
        gone = set(before) - set(after)
        changed = [n for n in set(before) & set(after) if before[n] != after[n]]
        print(f"\n  REVERTED -- the netlist changed.")
        if added:   print(f"    nets appeared: {sorted(added)[:5]}")
        if gone:    print(f"    nets vanished: {sorted(gone)[:5]}")
        if changed: print(f"    nets altered:  {sorted(changed)[:5]}")
        return 1
    os.remove(backup)
    print(f"\n  wrote {SCH}")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
