#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert an SVG logo into KiCad silkscreen polygons.

    .venv/bin/python tools/svg_to_silk.py --size 18 --at 174,55.5
    .venv/bin/python tools/svg_to_silk.py --size 18 --at 174,55.5 --apply
    .venv/bin/python tools/svg_to_silk.py --strip --apply

Needs the project venv for svgelements:  python3 -m venv .venv
                                         .venv/bin/pip install svgelements

SIZE COMES FROM absonus, NOT FROM A GUESS
-----------------------------------------
The ensō is plotted at 18.50 x 18.71 mm on the fabricated absonus v0.3 board,
measured off local/absonus-v0.3-pcb.pdf at 600 dpi against its stated 3.6000 in
width. caryatid's largest clear front-side square is 18 mm, which is within 3%.

That measurement also overturned an analysis of mine. Morphologically opening
the artwork at JLC's 0.15 mm silkscreen floor removes 27% of the ink at 18 mm
and breaks the rings into fragments, which said "unusable". A board fabricated
at 18.5 mm says otherwise: sub-floor features print imperfectly rather than not
at all, and on a brush-stroke ensō the imperfection reads as brush texture.
The model was worst-case, the board is evidence, and the board wins.

HOLES
-----
The artwork is one path of 314 subpaths under fill-rule evenodd, so it has
holes, and a KiCad gr_poly cannot express one -- every polygon on silkscreen is
ink, there is no erase. Holes are spliced into their parent contour with a
KEYHOLE: the closest pair of points between hole and parent is found and the
contour is re-entered through a doubled edge. The bridge has zero width, so it
prints as nothing, and the result is a single simple polygon per region.

Contour nesting is resolved by even-odd depth -- a contour inside an odd number
of others is a hole -- which is what fill-rule="evenodd" means and is why it
cannot be read off winding direction.
"""
import sys, os, re, math, uuid, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

NS  = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
TAG = "caryatid-logo"
OWNED = {str(uuid.uuid5(NS, f"{TAG}-{i}")) for i in range(4000)}
SEG = 0.06          # curve flattening, mm of chord error at final size
MINA = 0.0002         # drop contours smaller than this, mm^2 -- printer noise


def load_contours(path, size_mm):
    from svgelements import SVG, Path, Shape
    svg = SVG.parse(path)
    subs = []
    for el in svg.elements():
        if not isinstance(el, Shape): continue
        try: p = Path(el)
        except Exception: continue
        if len(p) == 0: continue
        for sp in p.as_subpaths():
            # Flatten SEGMENT BY SEGMENT with the vectorised npoint(). Sampling
            # the whole subpath with point(t) is ~260k parametric evaluations
            # over this artwork and does not finish in any reasonable time.
            pts = []
            for seg in Path(sp):
                try: ln = seg.length(error=1e-3)
                except Exception: ln = 0.0
                n = 1 if ln < 2 else min(200, max(2, int(ln / 1.5)))
                ts = [i / n for i in range(n + 1)]
                try:
                    for z in seg.npoint(ts): pts.append((float(z[0]), float(z[1])))
                except Exception:
                    for tt in ts:
                        z = seg.point(tt); pts.append((float(z.real), float(z.imag)))
            ded = [pts[0]] if pts else []
            for q2 in pts[1:]:
                if abs(q2[0]-ded[-1][0]) > 1e-6 or abs(q2[1]-ded[-1][1]) > 1e-6:
                    ded.append(q2)
            if len(ded) > 3: subs.append(ded)
    return subs


def area(p):
    s = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]; x2, y2 = p[(i+1) % len(p)]
        s += x1*y2 - x2*y1
    return s / 2


def inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i+1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2-x1)*(y-y1)/(y2-y1)+x1): c = not c
    return c


def keyhole(outer, hole):
    """Splice a hole into its parent through a zero-width bridge."""
    bi, bj, bd = 0, 0, None
    step_o = max(1, len(outer)//400); step_h = max(1, len(hole)//400)
    for i in range(0, len(outer), step_o):
        ox, oy = outer[i]
        for j in range(0, len(hole), step_h):
            hx, hy = hole[j]
            d = (ox-hx)**2 + (oy-hy)**2
            if bd is None or d < bd: bi, bj, bd = i, j, d
    h = hole[bj:] + hole[:bj+1]
    return outer[:bi+1] + h + [outer[bi]] + outer[bi+1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", default="local/enso-oro.svg")
    ap.add_argument("--size", type=float, default=18.0)
    ap.add_argument("--at", default="174,55.5")
    ap.add_argument("--layer", default="F.SilkS")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--strip", action="store_true")
    a = ap.parse_args()
    cx, cy = (float(v) for v in a.at.split(","))

    t = open(C.PCB).read()
    keep = [m for m in re.finditer(r"^\t\(gr_poly", t, re.M)]
    cut = []
    for m in keep:
        blk = C.sexp(t, m.start()+1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        # Match the ACTUAL per-polygon uuids. Comparing against a prefix of
        # uuid5(TAG) matches nothing -- uuid5("caryatid-logo") and
        # uuid5("caryatid-logo-0") share no prefix, so --strip silently found
        # zero and a re-run would have stacked a second logo on the first.
        if u and u.group(1) in OWNED:
            e = m.start()+1+len(blk)
            while e < len(t) and t[e] == "\n": e += 1
            cut.append((m.start(), e))
    for s, e in sorted(cut, reverse=True): t = t[:s] + t[e:]
    if cut: print(f"  removed {len(cut)} existing logo polygons")
    if a.strip:
        if a.apply: open(C.PCB, "w").write(t)
        else: print("  dry run -- pass --apply to write")
        return 0

    subs = load_contours(a.svg, a.size)
    xs = [p[0] for s in subs for p in s]; ys = [p[1] for s in subs for p in s]
    w, h = max(xs)-min(xs), max(ys)-min(ys)
    k = a.size / max(w, h)
    ox, oy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    subs = [[((x-ox)*k + cx, (y-oy)*k + cy) for x, y in s] for s in subs]
    subs = [s for s in subs if abs(area(s)) >= MINA]
    print(f"  {len(subs)} contours, artwork {w*k:.2f} x {h*k:.2f} mm at ({cx},{cy})")

    # even-odd depth: a contour inside an odd number of others is a hole.
    # Bounding boxes first -- the naive all-pairs point-in-polygon is 349x349
    # tests over contours of hundreds of points each and does not finish.
    reps = [s[0] for s in subs]
    bbs = [(min(p[0] for p in s), min(p[1] for p in s),
            max(p[0] for p in s), max(p[1] for p in s)) for s in subs]
    depth = []
    for i in range(len(subs)):
        rx, ry = reps[i]
        d = 0
        for j in range(len(subs)):
            if j == i: continue
            bx0, by0, bx1, by1 = bbs[j]
            if not (bx0 <= rx <= bx1 and by0 <= ry <= by1): continue
            if inside(reps[i], subs[j]): d += 1
        depth.append(d)
    solids = [i for i in range(len(subs)) if depth[i] % 2 == 0]
    holes  = [i for i in range(len(subs)) if depth[i] % 2 == 1]
    print(f"  {len(solids)} solid, {len(holes)} holes (even-odd)")

    polys = []
    for i in solids:
        poly = subs[i]
        bx0, by0, bx1, by1 = bbs[i]
        mine = [j for j in holes if depth[j] == depth[i]+1
                and bx0 <= reps[j][0] <= bx1 and by0 <= reps[j][1] <= by1
                and inside(reps[j], subs[i])]
        for j in mine: poly = keyhole(poly, subs[j])
        polys.append(poly)
    npts = sum(len(p) for p in polys)
    print(f"  {len(polys)} polygons after keyholing, {npts} points")

    chunks = []
    for n, poly in enumerate(polys):
        u = uuid.uuid5(NS, f"{TAG}-{n}")
        pts = "".join(f"\n\t\t\t\t(xy {x:.4f} {y:.4f})" for x, y in poly)
        chunks.append(f'\n\t(gr_poly\n\t\t(pts{pts}\n\t\t)\n'
                      f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n'
                      f'\t\t(fill solid)\n\t\t(layer "{a.layer}")\n\t\t(uuid "{u}")\n\t)')
    if not a.apply:
        print("\n  dry run -- pass --apply to write")
        return 0
    at = t.rindex("\n)")
    t = t[:at] + "".join(chunks) + t[at:]
    open(C.PCB, "w").write(t)
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"\n  wrote {len(polys)} polygons, paren balance {d}")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())