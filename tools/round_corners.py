#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Replace the square corners of a rectangular Edge.Cuts outline with arcs.

    python3 tools/round_corners.py                 # report only
    python3 tools/round_corners.py --apply
    python3 tools/round_corners.py --radius 5 --apply
    python3 tools/round_corners.py --radius 0 --apply    # square them again

WHY IT IS A TOOL AND NOT A ONE-SHOT
-----------------------------------
The radius is a judgement, not a derivation -- nothing on this board forces a
value. So the useful artefact is a script that can be re-run with a different
number rather than a set of coordinates typed in once. Running it twice with
the same radius is a no-op; running it with a new one re-rounds from the
implied rectangle, because it reconstructs the full rectangle from whatever
segments and arcs it finds before cutting the new corners.

WHAT CONSTRAINS THE RADIUS HERE
-------------------------------
Very little, which is worth stating so nobody re-derives it:

  * The four M3 mounting holes sit 5 mm in from both edges. A corner radius R
    reaches only R along each edge and R(sqrt2 - 1) diagonally, and the arc's
    angular span stops short of the diagonal direction the holes lie in -- so
    the holes keep their full 5 mm to the straight edge for any R below 5.
  * Nearest copper of any kind to a corner is 5.47 mm (the mounting holes
    themselves). Everything else is further.
  * The BUD CU-477's interior measures ~110 x 170 mm against a 150 x 90 board,
    so there is ~10 mm per side and the enclosure's own internal corner fillets
    cannot foul a square corner, let alone a rounded one.

The floor is the fab's router bit, not the design: JLC's standard bit gives a
1 mm minimum inside radius. An outside corner has no such limit, but a radius
below ~1 mm is not worth asking for.

AFTER RUNNING IT
----------------
Refill the zones. The ground pours clip to the board outline, and the corner
copper does not retreat on its own -- cycle.py's fill_zones() or a save in
KiCad both do it. check_board.py's edge-clearance check still models the
outline as a rectangle, so it reads the corners as being further out than they
are; that is conservative in the wrong direction, but with 5.47 mm of margin
it does not matter at any radius this board would use.
"""
import sys, os, re, math, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
TOL = 1e-6


def edge_blocks(t):
    """(start, end, kind, block) for every Edge.Cuts line and arc."""
    out = []
    for kind in ("gr_line", "gr_arc"):
        for m in re.finditer(rf"^\t\({kind}\b", t, re.M):
            blk = C.sexp(t, m.start() + 1)
            if '(layer "Edge.Cuts")' not in blk:
                continue
            end = m.start() + 1 + len(blk)
            while end < len(t) and t[end] == "\n":
                end += 1
            out.append((m.start(), end, kind, blk))
    return out


def xy(blk, tag):
    m = re.search(rf"\({tag} ([-\d.]+) ([-\d.]+)\)", blk)
    return (float(m.group(1)), float(m.group(2)))


def implied_rect(blks):
    """The rectangle the outline is cut from, whether or not it is rounded.

    Taking the bounding box of the endpoints would be wrong for an already
    rounded outline -- the corners are missing, so the box comes back short by
    the radius on each side. The straight segments still lie on the true
    rectangle's sides, so read the extremes off those instead."""
    xs, ys = [], []
    for _, _, kind, blk in blks:
        if kind != "gr_line":
            continue
        (x1, y1), (x2, y2) = xy(blk, "start"), xy(blk, "end")
        if abs(x1 - x2) < TOL:
            xs.append(x1)
        elif abs(y1 - y2) < TOL:
            ys.append(y1)
        else:
            return None, "outline has a diagonal segment -- not a rectangle"
    if len(set(round(v, 4) for v in xs)) != 2 or len(set(round(v, 4) for v in ys)) != 2:
        return None, f"expected 2 vertical and 2 horizontal sides, got {len(xs)} and {len(ys)}"
    return (min(xs), min(ys), max(xs), max(ys)), None


def emit(kind, pts, width, uid):
    # 6 decimals, not %g -- %g gives 6 SIGNIFICANT digits, which at x ~ 199 mm
    # truncates an arc mid point to 199.121 and leaves the radius 1 um out.
    body = "".join(f"\t\t({tag} {x:.6f} {y:.6f})\n" for tag, (x, y) in pts)
    return (f"\t({kind}\n{body}"
            f"\t\t(stroke\n\t\t\t(width {width:g})\n\t\t\t(type default)\n\t\t)\n"
            f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid}")\n\t)\n')


def build(x0, y0, x1, y1, r, width):
    """Four sides and, unless r is 0, four corner arcs.

    KiCad stores an arc as start/mid/end, so the mid point has to be computed
    rather than a centre and two angles given. Each mid sits on the 45 degree
    bisector at distance r from the arc centre."""
    d = r / math.sqrt(2)
    out = []
    sides = [(("start", (x0 + r, y0)), ("end", (x1 - r, y0))),      # top,    y = y0
             (("start", (x1, y0 + r)), ("end", (x1, y1 - r))),      # right,  x = x1
             (("start", (x1 - r, y1)), ("end", (x0 + r, y1))),      # bottom, y = y1
             (("start", (x0, y1 - r)), ("end", (x0, y0 + r)))]      # left,   x = x0
    for i, pts in enumerate(sides):
        out.append(emit("gr_line", pts, width, uuid.uuid5(NS, f"caryatid-edge-line-{i}")))
    if r <= 0:
        return out
    # (corner, arc centre, start, end) walking the same direction as the sides
    corners = [((x0, y0), (x0 + r, y0 + r), (x0, y0 + r), (x0 + r, y0)),
               ((x1, y0), (x1 - r, y0 + r), (x1 - r, y0), (x1, y0 + r)),
               ((x1, y1), (x1 - r, y1 - r), (x1, y1 - r), (x1 - r, y1)),
               ((x0, y1), (x0 + r, y1 - r), (x0 + r, y1), (x0, y1 - r))]
    for i, (cnr, (cx, cy), s, e) in enumerate(corners):
        mid = (cx + math.copysign(d, cnr[0] - cx), cy + math.copysign(d, cnr[1] - cy))
        out.append(emit("gr_arc", (("start", s), ("mid", mid), ("end", e)),
                        width, uuid.uuid5(NS, f"caryatid-edge-arc-{i}")))
    return out


def main():
    apply_ = "--apply" in sys.argv
    r = 3.0
    if "--radius" in sys.argv:
        r = float(sys.argv[sys.argv.index("--radius") + 1])

    t = open(C.PCB).read()
    blks = edge_blocks(t)
    lines = sum(1 for b in blks if b[2] == "gr_line")
    arcs = sum(1 for b in blks if b[2] == "gr_arc")
    print(f"  Edge.Cuts now       {lines} lines, {arcs} arcs")

    rect, err = implied_rect(blks)
    if err:
        print(f"  REFUSING: {err}")
        return 1
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    print(f"  implied rectangle   {w:g} x {h:g} mm at ({x0:g},{y0:g})")
    print(f"  corner radius       {r:g} mm")

    if r < 0 or 2 * r > min(w, h):
        print(f"  REFUSING: radius must be between 0 and {min(w, h) / 2:g} mm")
        return 1

    width = float(re.search(r"\(width ([\d.]+)\)", blks[0][3]).group(1))

    # every corner must keep its clearance to the nearest copper
    B = C.Board(C.PCB)
    worst = None
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        for p in B.parts:
            for pd in B.pads(p):
                d = math.hypot(pd["x"] - cx, pd["y"] - cy) - max(pd["w"], pd["h"]) / 2
                if worst is None or d < worst[0]:
                    worst = (d, f"{p['ref']}-{pd['num']}")
    reach = r * (math.sqrt(2) - 1)
    print(f"  arc reaches          {reach:.2f} mm diagonally into each corner")
    print(f"  nearest copper       {worst[0]:.2f} mm from a corner ({worst[1]})")
    if reach + C.EDGE_CLEARANCE > worst[0]:
        print(f"  REFUSING: {C.EDGE_CLEARANCE} mm edge clearance would be violated")
        return 1

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    for s, e, _, _ in sorted(blks, reverse=True):
        t = t[:s] + t[e:]
    at = min(b[0] for b in blks)
    t = t[:at] + "".join(build(x0, y0, x1, y1, r, width)) + t[at:]
    open(C.PCB, "w").write(t)

    d = sum(1 if ch == "(" else -1 if ch == ")" else 0 for ch in t)
    print(f"\n  wrote 4 sides and {0 if r <= 0 else 4} arcs, paren balance {d}")
    print("  refill the zones -- the pours do not retreat from the corners on their own")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())