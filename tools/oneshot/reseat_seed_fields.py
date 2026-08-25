#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bring seed.kicad_sch's passive fields back to the house offset.

    python3 tools/oneshot/reseat_seed_fields.py            # report
    python3 tools/oneshot/reseat_seed_fields.py --apply

THE DEFECT
----------
Every Reference and Value on seed.kicad_sch sits 30 mm from its symbol. On a
resistor whose body half-extent is 2.54 mm, that puts the designator 27.5 mm
away from a part 5 mm tall, with nine other identical resistors in between. You
cannot tell which R11 belongs to.

The rest of the repository agrees with itself and seed does not:

    audio.kicad_sch      Reference (+6.00, -12.00)   x39
    panel-io.kicad_sch   Reference (+6.00, -12.00)   x59
    power.kicad_sch      Reference (+6.00,  -6.00)   x26
    seed.kicad_sch       Reference (+6.00, -30.00)   x11    <- the odd one

So this is not a judgement about what looks nice. It is one sheet disagreeing
with ninety-eight instances of a convention, and the fix is to stop disagreeing.
Reference moves to (+6, -12) and Value to (+6, -9), matching audio and panel-io.

A1 AND A2 ARE LEFT EXACTLY WHERE THEY ARE, and that is the point of checking
rather than sweeping. They are the Daisy Seed sockets, half-extent 19.05 x 27.94,
so a field at -30.00 sits 2 mm above the symbol: correct placement for a part
that size. A blanket "move everything to -12" would have buried both labels
inside the socket body. Symbol extents come from the embedded library, per
docs/conventions.md rule 9.

WHY THIS IS SAFE WHERE THE LABEL MOVES WERE NOT
------------------------------------------------
A symbol field is annotation. It carries no connectivity, unlike a net label,
whose anchor is its attachment to the net. Nothing here can change the netlist.
The netlist is still exported and compared, because "cannot" and "did not" are
different claims and the check costs a second.

HOW I MISSED THIS FOR A WHOLE SESSION
--------------------------------------
I measured field-to-symbol distance across ALL FIVE SHEETS, got a median of
10.82 mm, concluded that was healthy, and dropped the check. It was healthy: for
the other four sheets. Aggregating across them drowned a sheet where the median
is 30.59 mm and every single field exceeds 20 mm. **A median over a mixed
population hid a uniform defect in one member of it.** Matt spotted it by eye
from the plot after I had explicitly told him the numbers said it was fine.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
SHEET = os.path.join(PCB_DIR, "seed.kicad_sch")
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

sys.path.insert(0, os.path.join(HERE, ".."))
import check_schematic as K

WANT = {"Reference": (6.0, -12.0), "Value": (6.0, -9.0)}
OLD = {"Reference": (6.0, -30.0), "Value": (6.0, -27.0)}
BIG = 10.0        # a symbol taller than this keeps its own offset


def netlist(tag):
    out = f"/tmp/reseat-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    t = open(out).read()
    return {m.group(1): sorted(re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
            for m in re.finditer(
                r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                t, re.S)}


def main():
    apply_ = "--apply" in sys.argv
    t = open(SHEET).read()
    ext = K.lib_extents(t)
    todo, kept = [], []

    for s in K.placed_symbols(t):
        if s["ref"].startswith("#"):
            continue
        ex, ey = ext.get(s["lib"], (0, 0))
        if ey >= BIG:
            kept.append((s["ref"], ey))
            continue
        new_blk = s["blk"]
        moved = []
        for field, (wx, wy) in WANT.items():
            for pm in re.finditer(r'\(property "%s" "' % field, new_blk):
                pb = K.sexp(new_blk, pm.start())
                am = re.search(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", pb)
                if not am:
                    break
                cx, cy = float(am.group(1)), float(am.group(2))
                ox, oy = round(cx - s["x"], 2), round(cy - s["y"], 2)
                if (ox, oy) != OLD[field]:
                    break            # not the offset we came to fix
                npb = (pb[:am.start()] +
                       f"(at {s['x'] + wx:g} {s['y'] + wy:g}{am.group(3)})" +
                       pb[am.end():])
                new_blk = new_blk[:pm.start()] + npb + new_blk[pm.start() + len(pb):]
                moved.append(f"{field} {oy:+.0f} -> {wy:+.0f}")
                break
        if moved:
            todo.append((s["blk"], new_blk, s["ref"], moved, ey))

    print(f"  {len(todo)} symbols to reseat on seed.kicad_sch")
    for _, _, ref, moved, ey in todo:
        print(f"      {ref:5} half-extent {ey:5.2f} mm   {', '.join(moved)}")
    if kept:
        print(f"\n  left alone, symbol taller than {BIG} mm so -30 is correct:")
        for ref, ey in kept:
            print(f"      {ref:5} half-extent {ey:.2f} mm")

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    bak = SHEET + ".bak"
    shutil.copy(SHEET, bak)
    for old, new, ref, _, _ in todo:
        if t.count(old) != 1:
            sys.exit(f"  {ref}: block is not unique -- not writing")
        t = t.replace(old, new, 1)
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    open(SHEET, "w").write(t)

    after = netlist("after")
    if before != after:
        shutil.copy(bak, SHEET)
        os.remove(bak)
        print("\n  REVERTED -- the netlist changed, which a field move must not do")
        return 1
    os.remove(bak)
    print(f"\n  wrote {SHEET}")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())