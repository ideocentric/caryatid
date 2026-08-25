#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pull the three debounce blocks onto the page, evenly.

    python3 tools/oneshot/refit_debounce_column.py            # report
    python3 tools/oneshot/refit_debounce_column.py --apply

THE DEFECT
----------
Matt: "C21 is off of the boundaries of the page." It is, and C21 is the small
half of it.

panel-io.kicad_sch carries three identical switch-debounce blocks -- connector,
pull-up, series resistor, 74HC14 gate, filter cap to ground -- repeating every
59.69 mm at rows 270.51, 330.20 and 389.89. A2 is 420 mm tall with the frame at
410. Three repeats of a 59.69 mm pitch starting at 270.51 do not fit, and the
third block's tail hangs off the bottom:

    C21     body to y 408.43, LOWER PIN to 411.48      past the frame
    GND     flag bottom at   419.10                    0.9 mm from the PAPER EDGE

Nothing is wrong with block 3. It is a faithful copy of a block that works. The
page is simply one repeat short, and the fix is the pitch, not the block.

THE PITCH
---------
Block 1 stays. Pitch drops 59.69 -> 53.34 mm, so rows land at 270.51, 323.85,
377.19 and block 3's GND bottom at 406.40, clear of the frame by 3.60 mm.

    block 1   unmoved
    block 2   up  6.35 mm
    block 3   up 12.70 mm

53.34 is 42 x 1.27 and 6.35 is 5 x 1.27, so everything stays on the grid the
sheet already uses. Note the ORIGINAL 59.69 pitch is 23.5 x 2.54: this sheet is
drawn on a 1.27 grid, not 2.54, and rows alternate on and off the coarser one.
Assuming 2.54 here would have pushed the whole column half a grid out of true.

54.61 mm also fits, at 1.06 mm of clearance. 53.34 was taken for the extra
2.5 mm, since the frame is a printed rule and butting a ground flag against it
reads as an error whether or not it technically clears.

WHY A WHOLE BLOCK MOVES AND NOT JUST C21
-----------------------------------------
Moving C21's tail alone was measured and rejected. The tail hangs 17.78 mm below
its row; lift it 12.70 and the cap lands on the horizontal signal wire running
through its own row at y 389.89, between R39 and the gate. Trading a part off
the page for a part on top of a wire is not a fix.

**Blocks are safe to move as units because nothing connects between them.** The
longest wire on the sheet is 5.08 mm and block-to-block continuity is carried by
net labels, not copper on the drawing. Verified: zero wires have their two
endpoints in different blocks.

MEMBERSHIP IS BY OFFSET SIGNATURE, NOT BY A Y RANGE
----------------------------------------------------
A y-range window does not partition these blocks, because consecutive blocks
OVERLAP vertically: each is ~66 mm tall on a 59.69 mm pitch, staggered in x. A
window around block 2 catches block 1's ground flag below it and block 3's +3V3
above it, and moving either would tear a neighbour apart.

So the three windows are compared first and their INTERSECTION taken. The bleed
drops out by construction: block 1 has no predecessor to donate a GND tail and
block 3 no successor to donate a +3V3 head, so those tuples are absent from one
window each and never reach the intersection. What survives is the true block
signature, and membership is then exact rather than approximate.

The offsets that would have been swept in by a window and are NOT block members:

    -38.10, -33.02   the previous block's GND flag and its wire
    +25.40, +30.48   the next block's +3V3 flag and its wire

FIELDS ARE ABSOLUTE, SO THEY MOVE WITH THE SYMBOL
--------------------------------------------------
In a .kicad_sch a property carries a PAGE coordinate, not an offset from its
symbol (conventions rule 9). A symbol moved without its properties leaves its
reference and value behind at the old y. Every `(at ...)` inside a symbol block
is shifted, which is right precisely because they are all absolute.

VERIFIED BY NETLIST. Exports before and after and reverts unless every net has
identical nodes.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
SHEET = os.path.join(PCB_DIR, "panel-io.kicad_sch")
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

sys.path.insert(0, os.path.join(HERE, ".."))
import check_schematic as K

ROWS = [270.51, 330.20, 389.89]
DELTA = [0.0, -6.35, -12.70]          # block 1 anchors the column
XLO, XHI = 30.0, 210.0                # the column's x span, clear of U3/C18
WIN = (-40.0, 32.0)                   # candidate window, deliberately generous
FRAME = 410.0                         # A2 is 420 tall, frame inset 10


def near(a, b, tol=0.005):
    return abs(a - b) < tol


def scan(t):
    """Every positioned element as (kind, x, y, start, block-text)."""
    out = []
    for m in re.finditer(r"^\t\(symbol\b", t, re.M):
        blk = K.sexp(t, m.start() + 1)
        if "(lib_id " not in blk:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
        lib = re.search(r'\(lib_id "([^"]+)"', blk).group(1)
        out.append(("sym:" + lib, float(at.group(1)), float(at.group(2)),
                    m.start() + 1, blk))
    for m in re.finditer(r"\(wire\b", t):
        blk = K.sexp(t, m.start())
        pts = [(float(a), float(b))
               for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", blk)]
        if len(pts) != 2:
            continue
        out.append(("wire", pts, None, m.start(), blk))
    for m in re.finditer(r'\((label|global_label|hierarchical_label) "', t):
        blk = K.sexp(t, m.start())
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
        out.append((m.group(1), float(at.group(1)), float(at.group(2)),
                    m.start(), blk))
    for m in re.finditer(r"\(junction\b", t):
        blk = K.sexp(t, m.start())
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
        out.append(("junction", float(at.group(1)), float(at.group(2)),
                    m.start(), blk))
    return out


def signature(els):
    """Intersection of the three blocks' (kind, x, offset) tuples."""
    sets = []
    for r in ROWS:
        s = set()
        for e in els:
            pts = [(e[1], e[2])] if e[0] != "wire" else e[1]
            for x, y in pts:
                if XLO <= x <= XHI and WIN[0] <= y - r <= WIN[1]:
                    s.add((e[0], round(x, 2), round(y - r, 2)))
        sets.append(s)
    core = sets[0] & sets[1] & sets[2]
    bleed = (sets[0] | sets[1] | sets[2]) - core
    return core, bleed


def shift_block(blk, dy):
    """Shift every (at x y ...) in a symbol block. They are ABSOLUTE."""
    def sub(m):
        return f"(at {m.group(1)} {float(m.group(2)) + dy:g}{m.group(3)})"
    return re.sub(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", sub, blk)


def netlist(tag):
    out = f"/tmp/refit-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    txt = open(out).read()
    return {m.group(1): sorted(re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
            for m in re.finditer(
                r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                txt, re.S)}


def main():
    apply_ = "--apply" in sys.argv
    t = open(SHEET).read()
    els = scan(t)
    core, bleed = signature(els)

    print(f"  block signature: {len(core)} elements, identical in all three")
    print(f"  window bleed rejected: {len(bleed)} tuples at offsets "
          f"{sorted({o for _, _, o in bleed})}")
    print(f"      these are the neighbouring blocks' GND tail and +3V3 head")

    todo, counts = [], {}
    for bi, (row, dy) in enumerate(zip(ROWS, DELTA), 1):
        if near(dy, 0.0):
            continue
        n = 0
        for e in els:
            kind = e[0]
            if kind == "wire":
                tags = [(kind, round(x, 2), round(y - row, 2)) for x, y in e[1]]
                inside = [tg in core for tg in tags]
                if not any(inside):
                    continue
                if not all(inside):
                    sys.exit(f"  a wire straddles block {bi}'s boundary at "
                             f"{e[1]} -- moving it would tear a net. Stopping.")
                new = e[4]
                for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", e[4]):
                    new = new.replace(f"(xy {a} {b})",
                                      f"(xy {a} {float(b) + dy:g})", 1)
            else:
                if (kind, round(e[1], 2), round(e[2] - row, 2)) not in core:
                    continue
                new = shift_block(e[4], dy)
            todo.append((e[3], e[4], new))
            n += 1
        counts[bi] = (row, dy, n)

    for bi, (row, dy, n) in sorted(counts.items()):
        print(f"\n  block {bi}: row {row:.2f} -> {row + dy:.2f}  ({dy:+.2f} mm), "
              f"{n} elements")

    # completeness: nothing may be left behind in a band that moved
    moved_pts = set()
    for _, old, _ in todo:
        for a, b in re.findall(r"\(at ([-\d.]+) ([-\d.]+)", old):
            moved_pts.add((round(float(a), 2), round(float(b), 2)))
        for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", old):
            moved_pts.add((round(float(a), 2), round(float(b), 2)))
    stranded = []
    for e in els:
        pts = [(e[1], e[2])] if e[0] != "wire" else e[1]
        for x, y in pts:
            if not (XLO <= x <= XHI):
                continue
            for bi, (row, dy, _) in counts.items():
                if WIN[0] <= y - row <= WIN[1] and \
                   (round(x, 2), round(y, 2)) not in moved_pts:
                    stranded.append((e[0], x, y, bi))
    if stranded:
        print(f"\n  {len(stranded)} element(s) sit in a moving band but are NOT "
              f"block members -- confirm each is a neighbour, not an omission:")
        for k, x, y, bi in sorted(set(stranded), key=lambda s: s[2]):
            print(f"      {k:22} at ({x:.2f}, {y:.2f})  near block {bi}")

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    bak = SHEET + ".bak"
    shutil.copy(SHEET, bak)
    for start, old, new in sorted(todo, key=lambda e: -e[0]):
        if t[start:start + len(old)] != old:
            sys.exit("  offset no longer holds what was measured -- not writing")
        t = t[:start] + new + t[start + len(old):]
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    open(SHEET, "w").write(t)

    after = netlist("after")
    if before != after:
        shutil.copy(bak, SHEET)
        os.remove(bak)
        ch = [n for n in set(before) & set(after) if before[n] != after[n]]
        print(f"\n  REVERTED -- the netlist changed.")
        print(f"    appeared: {sorted(set(after) - set(before))[:5]}")
        print(f"    vanished: {sorted(set(before) - set(after))[:5]}")
        print(f"    altered:  {sorted(ch)[:5]}")
        return 1
    os.remove(bak)
    print(f"\n  wrote {SHEET}")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())