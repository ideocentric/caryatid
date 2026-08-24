#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Move five net labels off the resistor bodies they clip.

    python3 tools/oneshot/unclip_gain_leg_labels.py            # report
    python3 tools/oneshot/unclip_gain_leg_labels.py --apply

THE DEFECT, AND HOW SMALL IT IS
--------------------------------
check_schematic.py found five labels overlapping the resistor they name:

    LEG_101_L  over R58     LEG_256_L  over R67
    LEG_101_R  over R62     LEG_256_R  over R68
    PGOOD_LEG  over R16      (seed.kicad_sch)

All five are the same shape. The label sits at rot 270 on the far end of a
5.08 mm wire, and its text runs BACK along that wire toward the resistor,
overshooting the wire's near end and clipping the body by **0.13 mm**. A hair,
and visible at plot scale as text touching a component outline.

WHY THE LABEL MOVES AND THE WIRE MOVES WITH IT
-----------------------------------------------
A label attaches to a net AT ITS ANCHOR. Rotating it would clear the resistor
without touching connectivity, and was rejected: the label would then point away
from the wire it belongs to, which trades a 0.13 mm overlap for a drawing that
reads wrong.

So the anchor moves 2.54 mm further from the resistor, one grid unit, and the
wire's FAR endpoint moves with it so the label stays on the wire end. The NEAR
endpoint does not move, because it is what touches the resistor pin, and moving
it is exactly how this kind of edit silently changes a netlist.

Checked before choosing the distance: at 2.54 mm none of the five lands on
another symbol, and the two that have a nearby reference (C24, C28) are cleared
by the checker afterwards rather than assumed.

VERIFIED BY NETLIST. Exports before and after and reverts unless every net has
identical nodes, the same gate move_jp6_clear_titleblock.py uses. Connectivity
in a schematic is positional and a plot cannot show a pin that came adrift.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

DY = 2.54          # one grid unit, away from the resistor

# (sheet, label, anchor x, anchor y). The wire endpoint at the same point
# moves with it; the other endpoint is the pin and stays put.
CASES = [
    ("audio.kicad_sch", "LEG_101_L", 219.71, 223.52),
    ("audio.kicad_sch", "LEG_101_R", 219.71, 373.38),
    ("audio.kicad_sch", "LEG_256_L", 530.86, 223.52),
    ("audio.kicad_sch", "LEG_256_R", 530.86, 373.38),
    ("seed.kicad_sch",  "PGOOD_LEG", 214.63, 199.39),
]


def near(a, b, tol=0.005):
    return abs(a - b) < tol


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


def netlist(tag):
    out = f"/tmp/unclip-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    t = open(out).read()
    nets = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                         t, re.S):
        nets[m.group(1)] = sorted(
            re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
    return nets


def plan(sheet):
    """(offset, old, new, description) for one sheet."""
    path = os.path.join(PCB_DIR, sheet)
    t = open(path).read()
    todo = []
    for sh, lab, x, y in CASES:
        if sh != sheet:
            continue
        hit = False
        for m in re.finditer(r'\((?:label|global_label|hierarchical_label) "%s"' % re.escape(lab), t):
            blk = sexp(t, m.start())
            am = re.search(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", blk)
            if not am:
                continue
            bx, by = float(am.group(1)), float(am.group(2))
            if not (near(bx, x) and near(by, y)):
                continue
            new = (blk[:am.start()] +
                   f"(at {bx:g} {by + DY:g}{am.group(3)})" + blk[am.end():])
            todo.append((m.start(), blk, new, f"label {lab}"))
            hit = True
            break
        if not hit:
            sys.exit(f"  {lab} is not at ({x}, {y}) in {sheet}. Stopping.")

        wired = False
        for m in re.finditer(r"\(wire\b", t):
            blk = sexp(t, m.start())
            pts = re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", blk)
            if len(pts) != 2:
                continue
            coords = [(float(a), float(b)) for a, b in pts]
            idx = [i for i, (px, py) in enumerate(coords)
                   if near(px, x) and near(py, y)]
            if not idx:
                continue
            a, b = pts[idx[0]]
            new = blk.replace(f"(xy {a} {b})", f"(xy {a} {float(b) + DY:g})", 1)
            todo.append((m.start(), blk, new, f"wire end at {lab}"))
            wired = True
            break
        if not wired:
            sys.exit(f"  no wire endpoint at {lab}'s anchor. Stopping.")
    return path, t, todo


def main():
    apply_ = "--apply" in sys.argv
    sheets = sorted({c[0] for c in CASES})
    work = {}
    for sh in sheets:
        path, t, todo = plan(sh)
        work[sh] = (path, t, todo)
        print(f"  {sh}: {len(todo)} elements move {DY:+.2f} mm")
        for _, _, _, what in todo:
            print(f"      {what}")

    expect = len(CASES) * 2
    got = sum(len(v[2]) for v in work.values())
    if got != expect:
        sys.exit(f"\n  expected {expect} elements, found {got}. Stopping.")

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    backups = {}
    for sh, (path, t, todo) in work.items():
        backups[sh] = path + ".bak"
        shutil.copy(path, backups[sh])
        for start, old, new, _ in sorted(todo, key=lambda e: -e[0]):
            if t[start:start + len(old)] != old:
                sys.exit("  offset no longer holds what was measured -- not writing")
            t = t[:start] + new + t[start + len(old):]
        d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
        if d != 0:
            sys.exit(f"  {sh} UNBALANCED ({d}) -- not writing")
        open(path, "w").write(t)

    after = netlist("after")
    if before != after:
        for sh, bak in backups.items():
            shutil.copy(bak, os.path.join(PCB_DIR, sh))
        for bak in backups.values():
            os.remove(bak)
        changed = [n for n in set(before) & set(after) if before[n] != after[n]]
        print(f"\n  REVERTED -- the netlist changed.")
        print(f"    appeared: {sorted(set(after)-set(before))[:5]}")
        print(f"    vanished: {sorted(set(before)-set(after))[:5]}")
        print(f"    altered:  {sorted(changed)[:5]}")
        return 1
    for bak in backups.values():
        os.remove(bak)
    print(f"\n  wrote {len(work)} sheet(s)")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())