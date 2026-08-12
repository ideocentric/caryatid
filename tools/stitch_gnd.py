#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Place GND stitching vias, so front-side ground pads reach the B.Cu plane.

    python3 tools/stitch_gnd.py             # propose and verify, write nothing
    python3 tools/stitch_gnd.py --apply     # insert the vias into the board

WHY THIS EXISTS
---------------
tools/export_dsn.py excludes GND from the DSN, with this justification:

    GND is excluded by default. B.Cu is a ground plane, so GND wants stitching
    vias, not 72 routed traces.

The first half is right and the second half never happened. Every component is
on the front, the plane is on the back, and NOTHING connected them: 152 vias on
the board, none on GND, and 53 front-side GND pads with no path down. Keeping
the router off ground was correct; leaving it there on the strength of a
mechanism that did not exist was not.

WHAT IS CHECKED
---------------
A via that exists is not the same as a via that reaches the plane. The one that
matters, and the one an "is there a via?" check would miss:

  * THE VIA MUST LAND IN THE MAIN GROUND ISLAND. The B.Cu fill is 13 separate
    islands, because the back layer also carries signal tracks. A via dropped
    into a small stranded island connects its pad to that island and to nothing
    else -- still unconnected, but now with a hole in the board. So the via
    centre is tested for containment in the LARGEST island specifically, with
    the via's own radius plus the zone clearance as margin, and a pad that
    cannot reach it is reported rather than stitched.

Also checked, against every other-net item: the via annulus on both layers, the
short trace from pad to via, hole-to-hole spacing against every other drilled
hole, and the board outline.

AFTER RUNNING THIS, REFILL THE ZONES (B in the board editor). The vias are on
the zone's own net, so the plane merges with them on the next fill -- but until
that fill happens the board still reports them unconnected.
"""
import sys, os, re, math, json, uuid, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board as C
from fanout import seg_rect_dist, seg_seg_dist, seg_pt_dist, pad_rect, Design, outward

VIA_D, VIA_DRILL = 0.70, 0.30      # Default class; 0.20 mm annular ring
TRACE_W          = 0.25            # Default class track
HOLE_TO_HOLE     = 0.45            # JLC pad hole-to-hole
ZONE_CLEAR       = 0.30            # from the zone definition
RING_START       = 0.75            # first radius tried, from the pad centre
RING_STEP        = 0.15
RING_MAX         = 6.0
ANGLES           = [a * math.pi / 24 for a in range(48)]   # 7.5 degree increments


def poly_contains(poly, p):
    x, y = p; inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi: inside = not inside
    return inside


def poly_edge_dist(poly, p):
    n = len(poly)
    return min(seg_pt_dist(poly[i], poly[(i + 1) % n], p) for i in range(n))


def islands(pcb_text, layer):
    """filled polygons of the GND zone on `layer`, largest first.

    Select by LAYER, never by position. This originally took the first zone in
    the file, which was the B.Cu plane until KiCad rewrote the board and put the
    new F.Cu pour first -- after which it was silently testing the wrong side."""
    z = None
    for m in re.finditer(r"^\t\(zone", pcb_text, re.M):
        blk = C.sexp(pcb_text, m.start() + 1)
        nm = re.search(r'\(net_name "([^"]*)"\)', blk)
        ly = re.search(r'\(layer "([^"]+)"\)', blk)
        if nm and ly and nm.group(1) == "GND" and ly.group(1) == layer:
            z = blk; break
    if z is None: return []
    out = []
    for fm in re.finditer(r"\(filled_polygon", z):
        blk = C.sexp(z, fm.start())
        pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", blk)]
        if len(pts) < 3: continue
        area = abs(sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1]
                       for i in range(len(pts)))) / 2
        out.append((area, pts))
    out.sort(key=lambda t: -t[0])
    return out


class Stitcher(Design):
    def __init__(self):
        super().__init__()
        self.isl = islands(self.t, "B.Cu")      # the plane a via must reach
        self.fisl = islands(self.t, "F.Cu")     # the front pour, for reporting
        self.vias = []
        for m in re.finditer(r"^\t\(via", self.t, re.M):
            b = C.sexp(self.t, m.start() + 1)
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", b)
            sz = re.search(r"\(size ([-\d.]+)\)", b)
            dr = re.search(r"\(drill ([-\d.]+)\)", b)
            n = re.search(r"\(net (\d+)\)", b)
            self.vias.append((float(at.group(1)), float(at.group(2)),
                              float(sz.group(1)), float(dr.group(1)),
                              int(n.group(1)) if n else -1))
        self.holes = [(pd["x"], pd["y"], pd["drill"])
                      for _, _, pd in self.pads if pd["drill"]]
        self.holes += [(v[0], v[1], v[3]) for v in self.vias]

    def via_ok(self, c, net, clr):
        """via annulus and hole at c, against everything not on `net`"""
        half = VIA_D / 2
        for ref, p, pd in self.pads:
            if not pd["net"] or pd["net"] == net: continue
            need = pd["clear"] or self.fp_clear.get(p["ref"], clr)
            if seg_rect_dist(c, c, pad_rect(pd)) - half - need < 0:
                return False, f"{ref}-{pd['num']} ({pd['net']})"
        for s, e, w, layer, nid in self.tracks:
            if nid == self.netid.get(net): continue
            if seg_pt_dist(s, e, c) - half - w / 2 - clr < 0:
                return False, f"track net {nid} on {layer}"
        for vx, vy, vs, vd, vn in self.vias:
            if vn == self.netid.get(net): continue
            if math.dist(c, (vx, vy)) - half - vs / 2 - clr < 0:
                return False, "via"
        for hx, hy, hd in self.holes:
            if math.dist(c, (hx, hy)) - VIA_DRILL / 2 - hd / 2 < HOLE_TO_HOLE:
                return False, "hole-to-hole"
        return True, None

    def island_of(self, pt):
        """the F.Cu pour island this point sits in, if any"""
        for i, (area, poly) in enumerate(self.fisl):
            if poly_contains(poly, pt): return i, area, poly
        return None

    def in_poly(self, poly, c, margin):
        return poly_contains(poly, c) and poly_edge_dist(poly, c) >= margin

    def reaches_plane(self, c):
        """inside the MAIN island, with room for the annulus and zone clearance"""
        if not self.isl: return False, "no GND fill -- fill the zones first"
        area, poly = self.isl[0]
        if not poly_contains(poly, c): return False, "outside the main ground island"
        if poly_edge_dist(poly, c) < VIA_D / 2 + ZONE_CLEAR:
            return False, "too close to the island edge"
        return True, None


def drc_unconnected_gnd():
    """(ref, pad) of every front-side GND pad KiCad reports as unconnected"""
    exe = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    exe = exe if os.path.exists(exe) else "kicad-cli"
    rpt = os.path.join(os.path.dirname(C.PCB), "stitch-drc.rpt")
    try:
        subprocess.run([exe, "pcb", "drc", "-o", rpt, C.PCB],
                       capture_output=True, timeout=900)
    except Exception:
        return None
    if not os.path.exists(rpt): return None
    out = set()
    for line in open(rpt):
        m = re.search(r"Pad (\S+) \[GND\] of (\S+) on F\.Cu", line)
        if m: out.add((m.group(2), m.group(1)))
    os.remove(rpt)
    return out


def main():
    apply_ = "--apply" in sys.argv
    S = Stitcher()
    if not S.isl:
        print("  the GND zone is not filled -- fill zones (B) and re-run"); return 1
    print(f"  B.Cu plane: {len(S.isl)} islands, main {S.isl[0][0]:.0f} mm2")
    print(f"  F.Cu pour : {len(S.fisl)} islands, main {S.fisl[0][0]:.0f} mm2\n"
          if S.fisl else "  F.Cu pour : none\n")

    clr = S.cls["Default"]["clearance"]
    x0, y0, x1, y1 = S.B.outline

    # Which pads still need one is a CONNECTIVITY question, and KiCad already
    # answers it. Re-deriving it here would mean reimplementing zone connectivity
    # -- thermal spokes, island merging, pad-to-fill contact -- and getting it
    # subtly wrong, which is how most of this board's bugs happened. Ask DRC.
    want = drc_unconnected_gnd()
    if want is None:
        print("  could not run DRC to find unconnected GND pads"); return 1
    print(f"  DRC reports {len(want)} front-side GND pads still unconnected\n")
    targets = [(ref, p, pd) for ref, p, pd in S.pads
               if pd["net"] == "GND" and not pd["drill"] and (ref, pd["num"]) in want]

    good, bad = [], []
    for ref, p, pd in sorted(targets, key=lambda x: (x[0], x[2]["num"])):
        a = (pd["x"], pd["y"])
        sol = None; why = None

        # A pad sitting in a stranded F.Cu island needs NO connecting trace: the
        # island already reaches it. The via only has to land somewhere in that
        # island that is also over the B.Cu plane. Searching for a via next to
        # the pad AND a clear straight trace to it was asking for two things
        # when one would do, and failing 9 times out of 10 because a 6 mm trace
        # across a routed board hits something.
        home = S.island_of(a)
        if home is not None:
            hi, harea, hpoly = home
            xs = [q[0] for q in hpoly]; ys = [q[1] for q in hpoly]
            margin = VIA_D / 2 + ZONE_CLEAR
            cands = []
            gx = xs and min(xs)
            step = 0.25
            n = 0
            yy = min(ys)
            while yy <= max(ys) and n < 60000:
                xx = min(xs)
                while xx <= max(xs) and n < 60000:
                    n += 1
                    cands.append((xx, yy)); xx += step
                yy += step
            cands.sort(key=lambda q: math.dist(q, a))
            for c in cands[:4000]:
                if not (x0 + 0.5 <= c[0] <= x1 - 0.5 and y0 + 0.5 <= c[1] <= y1 - 0.5): continue
                if not S.in_poly(hpoly, c, margin): continue
                ok, w = S.reaches_plane(c)
                if not ok: why = w; continue
                ok, w = S.via_ok(c, "GND", clr)
                if not ok: why = w; continue
                sol = (c, None); break
        if sol:
            good.append((ref, pd, a, sol[0], sol[1])); continue

        r = RING_START
        while r <= RING_MAX and not sol:
            ux, uy = outward(p, pd)
            base = math.atan2(uy, ux)
            for da in sorted(ANGLES, key=lambda t: abs(((t - 0) + math.pi) % (2*math.pi) - math.pi)):
                for sgn in (1, -1):
                    th = base + sgn * da
                    c = (a[0] + r * math.cos(th), a[1] + r * math.sin(th))
                    if not (x0 + 0.5 <= c[0] <= x1 - 0.5 and y0 + 0.5 <= c[1] <= y1 - 0.5):
                        continue
                    ok, w = S.via_ok(c, "GND", clr)
                    if not ok: why = w; continue
                    ok, w = S.reaches_plane(c)
                    if not ok: why = w; continue
                    ok, w = S.clear_of_everything(a, c, TRACE_W, "GND", clr)
                    if not ok: why = w[1]; continue
                    sol = (c, "trace"); break
                if sol: break
            r += RING_STEP
        if sol: good.append((ref, pd, a, sol[0], sol[1]))
        else:   bad.append((ref, pd, why))

    print(f"  {len(targets)} front-side GND pads")
    print(f"  {len(good)} stitched, {len(bad)} could not be\n")
    for ref, pd, why in bad:
        print(f"    {ref}-{pd['num']:<4} no via position: {why}")
    if bad: print()

    if not apply_:
        print("  dry run -- pass --apply to write them into the board")
        return 1 if bad else 0

    nid = S.netid["GND"]
    out = []
    for ref, pd, a, c, kind in good:
        if kind == "trace":
            out.append(f'\t(segment\n\t\t(start {a[0]:.4f} {a[1]:.4f})\n'
                       f'\t\t(end {c[0]:.4f} {c[1]:.4f})\n\t\t(width {TRACE_W})\n'
                       f'\t\t(layer "F.Cu")\n\t\t(net {nid})\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
        out.append(f'\t(via\n\t\t(at {c[0]:.4f} {c[1]:.4f})\n\t\t(size {VIA_D})\n'
                   f'\t\t(drill {VIA_DRILL})\n\t\t(layers "F.Cu" "B.Cu")\n'
                   f'\t\t(net {nid})\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
    t = S.t
    i = t.rfind("\n)")
    open(C.PCB, "w").write(t[:i] + "\n" + "".join(out).rstrip("\n") + t[i:])
    print(f"  wrote {len(good)} vias and {len(good)} traces into {os.path.relpath(C.PCB)}")
    print("  NOW REFILL THE ZONES (B) -- until then these still read unconnected")
    return 0


if __name__ == "__main__":
    sys.exit(main())