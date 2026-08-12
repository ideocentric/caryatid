#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Back up the board, then strip it back to placement only.

    python3 tools/reset_placement.py            # back up, strip, restore pours
    python3 tools/reset_placement.py --no-fill  # leave the pours unfilled (default)
    python3 tools/reset_placement.py --fill     # fill them before handing back

Gives a board with footprints, both ground pours and the outline, and no routed
copper at all -- the state to move parts around in. Every run first copies the
board to local/backups/ with a timestamp, and local/ is gitignored, so backups
accumulate there without touching the repo.

WHY IT RESTORES THE POURS
-------------------------
The F.Cu ground pour went missing between commit 098e603 and the following
cycle -- either during hand editing or in a cycle run whose backup has since
been overwritten, so which is not recoverable. Both pours are load-bearing:
stitch_gnd.py needs the F.Cu pour to decide which pads already reach ground,
and without it the last run left 51 pads wanting private vias. So this asserts
both exist rather than assuming, and rebuilds the F.Cu one from the B.Cu one if
it has gone.

The pours are left UNFILLED by default. An unfilled board is far easier to read
while placing, and cycle.py fills them anyway.
"""
import sys, os, re, uuid, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C
from cycle import strip_copper, fill_zones

BACKUPS = os.path.join(HERE, "..", "local", "backups")


def zones(t):
    out = []
    for m in re.finditer(r"^\t\(zone", t, re.M):
        z = C.sexp(t, m.start() + 1)
        lay = re.search(r'\(layer "([^"]+)"\)', z)
        net = re.search(r'\(net_name "([^"]*)"\)', z)
        out.append((lay.group(1) if lay else "?", net.group(1) if net else "", m.start(), z))
    return out


def unfill(t):
    """drop every filled_polygon; KiCad refills on demand and they are noise"""
    n = 0
    while True:
        m = re.search(r"\(filled_polygon", t)
        if not m: break
        blk = C.sexp(t, m.start())
        end = m.start() + len(blk)
        while end < len(t) and t[end] in "\n\t": end += 1
        t = t[:m.start()] + t[end:]
        n += 1
    return t, n


def main():
    t = open(C.PCB).read()

    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BACKUPS, f"caryatid-{stamp}.kicad_pcb")
    shutil.copy(C.PCB, dst)
    print(f"  backed up to local/backups/{os.path.basename(dst)}")

    n = strip_copper()
    print(f"  stripped {n} segments, arcs and vias")

    t = open(C.PCB).read()
    zs = zones(t)
    have = {z[0] for z in zs if z[1] == "GND"}
    print(f"  ground pours present: {sorted(have) or 'none'}")
    if "B.Cu" not in have:
        print("  NO B.Cu ground pour -- refusing to invent one; restore it by hand")
        return 1
    if "F.Cu" not in have:
        src = next(z for z in zs if z[0] == "B.Cu" and z[1] == "GND")[3]
        f = re.sub(r'\(layer "B\.Cu"\)', '(layer "F.Cu")', src, count=1)
        f = re.sub(r'\(uuid "[^"]*"\)', f'(uuid "{uuid.uuid4()}")', f, count=1)
        i = f.find("(filled_polygon")
        if i > 0: f = f[:i].rstrip() + "\n\t)"
        k = t.rfind("\n)")
        t = t[:k] + "\n\t" + f + t[k:]
        print("  rebuilt the F.Cu ground pour from the B.Cu one")

    if "--fill" not in sys.argv:
        t, nf = unfill(t)
        print(f"  removed {nf} filled polygons -- pours left unfilled for legibility")
    open(C.PCB, "w").write(t)

    if "--fill" in sys.argv:
        fill_zones()
        print("  zones filled")

    t = open(C.PCB).read()
    seg = len(re.findall(r"^\t\(segment", t, re.M))
    via = len(re.findall(r"^\t\(via", t, re.M))
    fp  = len(re.findall(r"^\t\(footprint", t, re.M))
    print(f"\n  board now: {fp} footprints, {len(zones(t))} zones, "
          f"{seg} segments, {via} vias")
    d = 0
    for ch in t:
        if ch == "(": d += 1
        elif ch == ")": d -= 1
    print(f"  paren balance: {d}")
    return 0 if d == 0 and seg == 0 and via == 0 else 1


if __name__ == "__main__":
    sys.exit(main())