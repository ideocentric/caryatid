#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lock or unlock routed copper, so a cycle can be surgical instead of total.

    python3 tools/lock_copper.py --lock-all --apply
    python3 tools/lock_copper.py --unlock-all --apply
    python3 tools/lock_copper.py --lock-except-holes --apply

WHY
---
cycle.py strips every UNLOCKED segment, via and arc, and that is the right
default: the route is a rendering of the placement, so it is regenerated after
every move. But once a board has been hand-routed the default throws that away
and hands the problem back to a router that did worse -- 25 unrouted against 4
here.

Locked copper survives step 1 AND is exported to Freerouting as `(type
protect)`, so the router works around it. Locking is therefore how you say
"re-route THIS and leave the rest alone".

--lock-except-holes IS THE SURGICAL CASE
-----------------------------------------
It locks everything except the copper that crosses a non-plated hole. Those
segments are exactly what a re-route should replace, because until
`844c90f` the DSN never told Freerouting the holes existed and it routed
across them -- VBAT through BT1's bolt hole, twice, at 0.000 mm.

The exclusion zone is computed the same way export_dsn.py fences it: drill
radius + the board's own `min_hole_clearance`, which is what DRC measures --
hole edge to track edge. The two agree by construction rather than by having
been typed twice.

A segment is freed if its swept copper enters that zone: distance from the hole
centre to the segment, minus half the track width, less than the radius.

AFTERWARDS. `--unlock-all` puts the board back. Leaving 1000 items locked would
make the next full cycle a no-op and the reason would not be obvious.
"""
import sys, os, re, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

PRO = os.path.join(os.path.dirname(C.PCB), "caryatid.kicad_pro")


def npth_zones():
    """(x, y, radius) for every non-plated hole, radius = drill/2 + clearance."""
    B = C.Board(C.PCB)
    clr = json.load(open(PRO))["board"]["design_settings"]["rules"]["min_hole_clearance"]
    out = []
    for p in B.parts:
        for m in re.finditer(r'\(pad "', p["blk"]):
            pb = C.sexp(p["blk"], m.start())
            kind = re.match(r'\(pad "[^"]*" (\S+)', pb)
            if not kind or kind.group(1) != "np_thru_hole":
                continue
            am = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
            dr = re.search(r"\(drill ([-\d.]+)\)", pb)
            if not (am and dr):
                continue
            px, py = float(am.group(1)), float(am.group(2))
            th = math.radians(p["rot"])
            cs, sn = math.cos(th), math.sin(th)
            out.append((p["x"] + px * cs + py * sn, p["y"] - px * sn + py * cs,
                        float(dr.group(1)) / 2 + clr, p["ref"]))
    return out


def seg_point_dist(x1, y1, x2, y2, px, py):
    vx, vy = x2 - x1, y2 - y1
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def main():
    apply_ = "--apply" in sys.argv
    lock_all = "--lock-all" in sys.argv
    unlock_all = "--unlock-all" in sys.argv
    except_holes = "--lock-except-holes" in sys.argv
    if sum((lock_all, unlock_all, except_holes)) != 1:
        sys.exit("  pick exactly one of --lock-all, --unlock-all, --lock-except-holes")

    t = open(C.PCB).read()
    zones = npth_zones() if except_holes else []
    if zones:
        print(f"  {len(zones)} non-plated hole(s), exclusion radius "
              f"{zones[0][2]:.3f} mm")

    freed, locked, unlocked, spans = [], 0, 0, []
    for kind in ("segment", "via", "arc"):
        for m in re.finditer(rf"^\t\({kind}\b", t, re.M):
            spans.append((m.start() + 1, C.sexp(t, m.start() + 1), kind))
    # SORT. Collected per kind, the list runs segments-then-vias-then-arcs, not
    # file order -- and the rebuild below walks forward with a `last` cursor, so
    # an out-of-order start silently drops the text between them. The first
    # version of this did exactly that and produced a board with 924 segments
    # where 926 went in. Never rebuild a file from spans that are not sorted.
    spans.sort(key=lambda s: s[0])

    out = []
    last = 0
    for start, blk, kind in spans:
        want_lock = lock_all or except_holes
        if except_holes and kind == "segment":
            s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            w = re.search(r"\(width ([\d.]+)\)", blk)
            if s and e and w:
                half = float(w.group(1)) / 2
                for hx, hy, rad, ref in zones:
                    d = seg_point_dist(float(s.group(1)), float(s.group(2)),
                                       float(e.group(1)), float(e.group(2)), hx, hy)
                    if d - half < rad:
                        want_lock = False
                        net = re.search(r"\(net (\d+)\)", blk)
                        freed.append((ref, net.group(1) if net else "?",
                                      s.group(1), s.group(2)))
                        break
        if unlock_all:
            want_lock = False

        has = "(locked yes)" in blk
        new = blk
        if want_lock and not has:
            head = blk.index("\n") + 1
            new = blk[:head] + "\t\t(locked yes)\n" + blk[head:]
            locked += 1
        elif not want_lock and has:
            new = blk.replace("\t\t(locked yes)\n", "", 1)
            unlocked += 1
        out.append(t[last:start]); out.append(new)
        last = start + len(blk)
    out.append(t[last:])
    t = "".join(out)

    print(f"  {len(spans)} copper items: +{locked} locked, -{unlocked} unlocked")
    if freed:
        print(f"  left UNLOCKED because they cross a hole ({len(freed)}):")
        for ref, net, sx, sy in freed:
            print(f"      net {net} at ({sx}, {sy})  crosses {ref}")
    # THE ONLY LEGAL DIFFERENCE IS `(locked yes)` LINES. A paren-balance check
    # is not enough -- the span-ordering bug above produced a file that balanced
    # and was still missing two segments. So compare the two texts with every
    # locked line stripped: they must be identical, byte for byte.
    strip_locks = lambda s: s.replace("\t\t(locked yes)\n", "")
    if strip_locks(t) != strip_locks(open(C.PCB).read()):
        sys.exit("  THE FILE CHANGED BEYOND LOCK LINES -- not writing. "
                 "Something other than locking was altered.")
    for kind, want in (("segment", None), ("via", None), ("footprint", None)):
        a = len(re.findall(rf"^\t\({kind}\b", t, re.M))
        b = len(re.findall(rf"^\t\({kind}\b", open(C.PCB).read(), re.M))
        if a != b:
            sys.exit(f"  {kind} count changed {b} -> {a} -- not writing")

    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0
    open(C.PCB, "w").write(t)
    print(f"  wrote {C.PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())