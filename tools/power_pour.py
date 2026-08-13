#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pour the boost-converter power nets as copper zones instead of routing them.

    python3 tools/power_pour.py             # propose and verify, write nothing
    python3 tools/power_pour.py --apply

WHY POUR RATHER THAN ROUTE
--------------------------
VOUT, /power/SW and +5V_RAW are 0.80 to 1.20 mm nets in a cluster about 15 mm
across. The router keeps failing them, and even when it succeeds a track is the
wrong shape for the job: a 1 A path between pads a couple of millimetres apart
wants copper, not a wire. Pouring them also takes three of the hardest nets out
of the router's problem entirely, which is what frees a path for /power/EN_SW.

SW IS THE EXCEPTION AND IT MATTERS
----------------------------------
The obvious reading is "pour them all for maximum coverage". That is right for
VOUT and +5V_RAW, which are quiet DC nodes where more copper is lower impedance
and nothing else.

It is exactly wrong for SW. The switch node swings 0 to 5 V at 1 MHz with fast
edges, so its copper area IS the radiating antenna of this design -- every
switching layout rule reduces to keeping it as small as the current allows. Here
U2-5 and L1-2 are 2.31 mm apart, so SW should be a tight bridge between two pads
and nothing more. SW_MARGIN is therefore small on purpose; raising it to match
the others would be a regression, not an improvement.

PRIORITY
--------
Each pour is priority 1, above the GND plane at 0, so ground yields to it rather
than flooding through. KiCad enforces clearance between zones of different nets
when filling, so the outlines here can be generous without shorting anything --
generous is the point for VOUT and +5V_RAW.
"""
import sys, os, re, math, uuid, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

# net -> (part to cluster around, radius to gather pads within, pour WIDTH)
#
# The width is the thickness of copper laid along the path between pads, not a
# margin round a bounding box. A box round VOUT's four pads swallowed the whole
# SOT-563 -- SW, EN_SW and +5V_RAW included -- and the three boxes overlapped
# each other. Pouring along the connections instead keeps each net to the shape
# the current actually wants and leaves the neighbouring pads alone.
POURS = [
    ("VOUT",       "U2", 12.0, 2.50),
    ("+5V_RAW",    "U2", 12.0, 2.50),
    ("/power/SW",  "U2", 12.0, 1.50),   # SMALL ON PURPOSE -- see the header
]
PRIORITY = 1


def mst(points):
    """minimum spanning tree edges over the pad centres"""
    if len(points) < 2: return []
    inside, out = [0], list(range(1, len(points)))
    edges = []
    while out:
        best = min(((i, j) for i in inside for j in out),
                   key=lambda e: math.dist(points[e[0]], points[e[1]]))
        edges.append(best); inside.append(best[1]); out.remove(best[1])
    return edges


def capsule(a, b, w):
    """rotated rectangle of width w along a-b, as four points"""
    dx, dy = b[0]-a[0], b[1]-a[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx/L, dy/L
    nx, ny = -uy*w/2, ux*w/2
    ex, ey = ux*w/2, uy*w/2          # overhang the ends so pads are covered
    return [(a[0]-ex+nx, a[1]-ey+ny), (b[0]+ex+nx, b[1]+ey+ny),
            (b[0]+ex-nx, b[1]+ey-ny), (a[0]-ex-nx, a[1]-ey-ny)]


def hull(points):
    """convex hull, so each net becomes ONE polygon instead of overlapping
    capsules. Emitting a zone per capsule gave 27 same-net zones_intersect
    warnings -- electrically harmless, since they merge on fill, but noise in
    every DRC report from then on."""
    pts = sorted(set(points))
    if len(pts) < 3: return pts
    def half(ps):
        out = []
        for q in ps:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx-ax)*(q[1]-ay) - (by-ay)*(q[0]-ax) <= 0: out.pop()
                else: break
            out.append(q)
        return out
    return half(pts)[:-1] + half(pts[::-1])[:-1]


def zones(t):
    out = []
    for m in re.finditer(r"^\t\(zone", t, re.M):
        z = C.sexp(t, m.start() + 1)
        nm = re.search(r'\(net_name "([^"]*)"\)', z)
        ly = re.search(r'\(layer "([^"]+)"\)', z)
        out.append((nm.group(1) if nm else "", ly.group(1) if ly else "", z))
    return out


def main():
    apply_ = "--apply" in sys.argv
    B = C.Board(C.PCB)
    t = B.t
    netid = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
    have = {(n, l) for n, l, _ in zones(t)}

    print(f"  {'net':<13}{'pads':>5}{'extent':>22}{'margin':>8}   outline")
    made = []
    for net, around, radius, margin in POURS:
        if (net, "F.Cu") in have:
            print(f"  {net:<13}already poured on F.Cu -- skipping"); continue
        anchor = next((p for p in B.parts if p["ref"] == around), None)
        if anchor is None:
            print(f"  {net:<13}no {around} on the board"); continue
        pads = [(pd, p["ref"]) for p in B.parts for pd in B.pads(p)
                if pd["net"] == net
                and math.dist((pd["x"], pd["y"]), (anchor["x"], anchor["y"])) <= radius]
        if len(pads) < 2:
            print(f"  {net:<13}only {len(pads)} pad(s) within {radius} mm of {around}"); continue
        pts = [(q[0]["x"], q[0]["y"]) for q in pads]
        polys = [capsule(pts[i], pts[j], margin) for i, j in mst(pts)]
        # widen each pad's own footprint into the pour so the bond is solid
        for q, _ in pads:
            hw, hh = max(q["w"], margin)/2, max(q["h"], margin)/2
            polys.append([(q["x"]-hw, q["y"]-hh), (q["x"]+hw, q["y"]-hh),
                          (q["x"]+hw, q["y"]+hh), (q["x"]-hw, q["y"]+hh)])
        refs = ",".join(sorted({f"{r}-{q['num']}" for q, r in pads}))
        span = sum(math.dist(pts[i], pts[j]) for i, j in mst(pts))
        print(f"  {net:<13}{len(pads):5d}  {len(polys):3d} polys, {span:5.1f} mm of path"
              f"{margin:8.2f}   {refs}")
        made.append((net, [hull([q for poly in polys for q in poly])]))

    if not made:
        print("\n  nothing to do"); return 0

    # a pour must not swallow a pad of another net -- KiCad would pull back, but
    # a zone drawn over a foreign pad is a drawing mistake, so say so
    def inpoly(poly, q):
        x, y = q; inside = False; n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]; x1, y1 = poly[(i+1) % n]
            if (y0 > y) != (y1 > y):
                xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                if x < xi: inside = not inside
        return inside
    bad = 0
    for net, polys in made:
        for p in B.parts:
            for pd in B.pads(p):
                if not pd["net"] or pd["net"] == net or pd["net"] == "GND": continue
                if any(inpoly(poly, (pd["x"], pd["y"])) for poly in polys):
                    print(f"    {net} pour covers {p['ref']}-{pd['num']} ({pd['net']})")
                    bad += 1
    if bad:
        print(f"\n  {bad} foreign pad(s) inside a pour outline -- KiCad will clear round them,"
              f"\n  but check by eye that this is what you meant")

    if not apply_:
        print("\n  dry run -- pass --apply to add the zones")
        return 0

    blocks = []
    for net, polys in made:
      for poly in polys:
        pts = " ".join(f"(xy {q[0]:.4f} {q[1]:.4f})" for q in poly)
        blocks.append(
            f'\t(zone\n\t\t(net {netid[net]})\n\t\t(net_name "{net}")\n'
            f'\t\t(layer "F.Cu")\n\t\t(uuid "{uuid.uuid4()}")\n'
            f'\t\t(name "{net} pour")\n\t\t(hatch edge 0.5)\n'
            f'\t\t(priority {PRIORITY})\n'
            f'\t\t(connect_pads yes\n\t\t\t(clearance 0.2)\n\t\t)\n'
            f'\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n'
            f'\t\t(fill yes\n\t\t\t(thermal_gap 0.3)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n'
            f'\t\t(polygon\n\t\t\t(pts\n\t\t\t\t{pts}\n\t\t\t)\n\t\t)\n\t)\n')
    i = t.rfind("\n)")
    open(C.PCB, "w").write(t[:i] + "\n" + "".join(blocks).rstrip("\n") + t[i:])
    print(f"\n  added {len(blocks)} pours at priority {PRIORITY}")
    print("  refill the zones, and re-export -- export_dsn.py drops poured nets"
          "\n  from the DSN so the router does not also wire them")
    return 0


if __name__ == "__main__":
    sys.exit(main())