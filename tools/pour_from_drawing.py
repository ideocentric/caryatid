#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn hand-drawn F.Cu polygons into net-assigned copper pours.

    python3 tools/pour_from_drawing.py            # review, write nothing
    python3 tools/pour_from_drawing.py --apply

Draw the copper you want in the board editor as filled polygons on F.Cu, one per
net, each enclosing only that net's pads. This reads them back, works out which
net each belongs to from the pads inside it, and rewrites them as zones.

WHY NOT GENERATE THE SHAPES
---------------------------
tools/power_pour.py tried. Around a SOT-563 the pads of six nets interleave at
0.5 mm pitch, and any shape derived from pad positions -- bounding box, convex
hull, capsules along a spanning tree -- covers its neighbours. The box version
swallowed 16 foreign pads, the hull version 8. A hand-drawn outline weaves
between the pins and covers none, because a person can see the gap and an
algorithm fitting a convex shape to scattered points cannot.

So this does not compute geometry. It only classifies and converts.

A gr_poly ON A COPPER LAYER IS COPPER WITH NO NET. Left as drawn, these would
fabricate as isolated islands -- so converting them is a correctness fix, not a
convenience.

WHAT IS CHECKED
---------------
  * each polygon must enclose pads of EXACTLY ONE net; zero nets or two nets is
    an error, not a guess
  * the resulting zone gets that net, at a priority above the ground plane so
    ground yields to it rather than flooding through
  * the source gr_poly is removed, so the copper exists once and has a net
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

PRIORITY = 1
CLEARANCE = 0.2      # default; overridden per-pour below

# A pour hugging a fine-pitch part must use THAT PART'S clearance, not the
# board default. Beside U2-5 the corridor between its neighbours is
# 2 x (0.5 pitch - 0.175 half-pad - clearance):
#
#   clearance 0.20  ->  0.250 mm, exactly min_thickness -- fills or vanishes
#   clearance 0.15  ->  0.350 mm, comfortable
#
# U2 carries a 0.15 mm footprint override for exactly this reason, and a pour
# that ignores it is 0.05 mm too tight to survive the fill. So take the
# tightest override among the parts the pour actually touches.


def inpoly(poly, q):
    x, y = q; inside = False; n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi: inside = not inside
    return inside


def main():
    apply_ = "--apply" in sys.argv
    # Nets to DELETE the drawing for rather than pour. FB is the feedback divider
    # tap -- the highest-impedance node in a switching regulator and the one most
    # willing to pick up the switch node. It escapes fine as a track, and copper
    # there buys nothing but coupling area.
    skip = []
    if "--skip" in sys.argv:
        skip = sys.argv[sys.argv.index("--skip") + 1].split(",")
    B = C.Board(C.PCB)
    t = B.t
    netid = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
    pads = [(p["ref"], pd) for p in B.parts for pd in B.pads(p) if pd["net"]]
    D_fp = {}
    for p in B.parts:
        spans = [q["span"] for q in B.pads(p)]
        for m in re.finditer(r"\(clearance ([\d.]+)\)", p["blk"]):
            if any(s <= m.start() < e for s, e in spans): continue
            D_fp[p["ref"]] = float(m.group(1)); break

    found = []
    for m in re.finditer(r"^\t\(gr_poly", t, re.M):
        blk = C.sexp(t, m.start() + 1)
        if '"F.Cu"' not in blk: continue
        pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", blk)]
        if len(pts) < 3: continue
        found.append((m.start(), len(blk) + 1, pts))

    print(f"  {len(found)} polygon(s) on F.Cu\n")
    print(f"  {'#':>2}  {'net':<16}{'pts':>4}{'area':>9}   pads enclosed")
    ok, bad, drop = [], [], []
    for i, (start, length, pts) in enumerate(found, 1):
        inside = [(r, pd) for r, pd in pads if inpoly(pts, (pd["x"], pd["y"]))]
        nets = sorted({pd["net"] for _, pd in inside})
        area = abs(sum(pts[k][0]*pts[(k+1) % len(pts)][1] - pts[(k+1) % len(pts)][0]*pts[k][1]
                       for k in range(len(pts)))) / 2
        refs = ", ".join(f"{r}-{pd['num']}" for r, pd in inside)
        fpclr = [D_fp.get(r) for r, _ in inside if D_fp.get(r)]
        clearance = min([CLEARANCE] + fpclr)
        if len(nets) == 1 and nets[0] in skip:
            print(f"  {i:>2}  {nets[0]:<16}{len(pts):>4}{area:8.2f}   SKIPPED, drawing left in place")
        elif len(nets) == 1:
            ok.append((start, length, pts, nets[0], clearance))
            tag = f"   clr {clearance}" if clearance != CLEARANCE else ""
            print(f"  {i:>2}  {nets[0]:<16}{len(pts):>4}{area:8.2f}   {refs}{tag}")
        else:
            bad.append((i, nets))
            why = "encloses no pad" if not nets else f"spans {len(nets)} nets: {', '.join(nets)}"
            print(f"  {i:>2}  {'??':<16}{len(pts):>4}{area:8.2f}   {why}")

    if bad:
        print(f"\n  {len(bad)} polygon(s) cannot be classified -- fix or delete them first.")
        print("  A pour has one net; guessing which would be worse than stopping.")
        return 1
    if not ok:
        print("\n  nothing to convert"); return 0

    missing = [n for _, _, _, n, _ in ok if n not in netid]
    if missing:
        print(f"\n  net(s) not on this board: {missing}"); return 1

    if not apply_:
        print("\n  dry run -- pass --apply to convert these to pours")
        return 0

    # rebuild the file: drop each gr_poly, append a zone with the same outline
    blocks = []
    for _, _, pts, net, clearance in ok:
        xy = " ".join(f"(xy {q[0]:.4f} {q[1]:.4f})" for q in pts)
        blocks.append(
            f'\t(zone\n\t\t(net {netid[net]})\n\t\t(net_name "{net}")\n'
            f'\t\t(layer "F.Cu")\n\t\t(uuid "{uuid.uuid4()}")\n'
            f'\t\t(name "{net} pour")\n\t\t(hatch edge 0.5)\n'
            f'\t\t(priority {PRIORITY})\n'
            f'\t\t(connect_pads yes\n\t\t\t(clearance {clearance})\n\t\t)\n'
            f'\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n'
            f'\t\t(fill yes\n\t\t\t(thermal_gap 0.3)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n'
            f'\t\t(polygon\n\t\t\t(pts\n\t\t\t\t{xy}\n\t\t\t)\n\t\t)\n\t)\n')

    for start, length in sorted([(s, l) for s, l, _, _, _ in ok] + drop, key=lambda z: -z[0]):
        end = start + length
        while end < len(t) and t[end] == "\n": end += 1
        t = t[:start] + t[end:]
    i = t.rfind("\n)")
    open(C.PCB, "w").write(t[:i] + "\n" + "".join(blocks).rstrip("\n") + t[i:])
    print(f"\n  converted {len(ok)} drawn polygons into pours at priority {PRIORITY}"
          + (f", deleted {len(drop)} left as tracks" if drop else ""))
    print("  the gr_poly graphics are gone -- the copper now exists once, with a net")
    print("  refill zones next")
    return 0


if __name__ == "__main__":
    sys.exit(main())