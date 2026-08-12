#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Route necked escapes out of fine-pitch pads, so Freerouting can take over.

    python3 tools/fanout.py             # propose and verify, write nothing
    python3 tools/fanout.py --apply     # insert the escapes into the board

WHY THIS EXISTS
---------------
Freerouting routes a net at one width: the width of its class. It has no
neck-down. So a HighCurrent net at 1.20 mm cannot leave U1's 0.25 mm QFN pads
on 0.5 mm pitch, and the router simply fails those connections -- eleven of the
thirteen unrouted connections in the last run were at U1 or U2.

The fix is the standard one: escape each fine-pitch pad by hand at a width that
fits between its neighbours, run outward until the package no longer constrains
anything, widen to the class width, and mark the result protected so the router
starts from there instead of from the pad.

WHAT IS CHECKED, AND WHY EACH CHECK IS HERE
-------------------------------------------
Two earlier attempts at this measurement were wrong in the same way -- a model
that captured one thing and ignored another:

  * "track wider than the pad" is NOT the criterion. What binds is clearance to
    the NEIGHBOURING pad, which is a different question with a different answer.
  * measuring the widest track that fits SYMMETRICALLY around the pad centre
    reported 0.070 mm at U1 -- below JLC's floor, i.e. no legal escape exists.
    That was nonsense: the nearest neighbour it found was U1-17, the exposed
    thermal pad, which sits BEHIND the pins. An escape runs outward, away from
    it. A swept trace has a direction; a disc does not.

So every proposal here is verified as a swept rectangle along its actual path,
against every other-net pad and every other-net track on the same layer.
"""
import sys, os, re, math, json, fnmatch, uuid
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board as C

JLC_MIN_TRACK = 0.10
# Escape widths, NARROWEST-ADEQUATE first. Taking the widest that fits is the
# mistake that cost more connections than the fanout gained: a 0.30 mm escape
# per pad left the signal pins beside it 0.025 mm of slack, and 0.90 mm from a
# tied pair left 0.013 mm. The neck only has to carry what the pads themselves
# provide -- it is 1 mm long between a pad and a wide plane, and the pad is the
# real constriction -- so the target is (pad width x how many pads feed it).
# Everything past that is room taken from a neighbour that also has to get out.
ESCAPE_WIDTHS = (0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 0.90, 1.00, 1.20)
NEIGHBOUR_SLACK = 0.05    # every other pad must still escape with this to spare
LINK_W        = 0.20      # ties adjacent same-net pads together
MAX_LINK_MM   = 2.0
WIDE_STUB_MM  = 0.60      # length of class-width copper proved at the far end
STEP          = 0.05
MAX_REACH     = 4.0
MIN_REACH0    = 0.0       # grows on retry: pushes the WIDE copper off the pad row
RETRY_STEP    = 0.10
RETRIES       = 12


# --- geometry ---------------------------------------------------------------
def seg_pt_dist(a, b, p):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg_dist(a, b, c, d):
    def cross(o, p, q): return (p[0]-o[0])*(q[1]-o[1]) - (p[1]-o[1])*(q[0]-o[0])
    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0                      # they cross
    return min(seg_pt_dist(a, b, c), seg_pt_dist(a, b, d),
               seg_pt_dist(c, d, a), seg_pt_dist(c, d, b))


def seg_rect_dist(a, b, r):
    """distance from segment a-b to axis-aligned rect r=(x0,y0,x1,y1)"""
    x0, y0, x1, y1 = r
    for p in (a, b):                    # endpoint inside the rect
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1: return 0.0
    edges = (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))
    return min(seg_seg_dist(a, b, e[0], e[1]) for e in edges)


def pad_rect(pd):
    return (pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2,
            pd["x"] + pd["w"] / 2, pd["y"] + pd["h"] / 2)


# --- board ------------------------------------------------------------------
class Design:
    def __init__(self):
        self.B = C.Board(C.PCB)
        self.t = self.B.t
        pro = json.load(open(C.PRO))["net_settings"]
        self.cls = {c["name"]: c for c in pro["classes"]}
        self.pats = pro.get("netclass_patterns", [])
        self.netid = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', self.t)}
        # Footprint-level clearance overrides, by reference. Two traps here: the
        # ones in this board are written at ONE tab, not two (indentation is
        # cosmetic in s-expressions, paren nesting is what counts), and a
        # (clearance ...) may also appear inside a pad, which is a per-pad
        # override and a different thing. So: any clearance in the footprint
        # block that is NOT inside a pad's span is the footprint-level one.
        self.fp_clear = {}
        for p in self.B.parts:
            spans = [pd["span"] for pd in self.B.pads(p)]
            for m in re.finditer(r"\(clearance ([\d.]+)\)", p["blk"]):
                if any(s <= m.start() < e for s, e in spans): continue
                self.fp_clear[p["ref"]] = float(m.group(1))
                break
        self.pads = [(p["ref"], p, pd) for p in self.B.parts for pd in self.B.pads(p)]
        self.tracks = []
        for m in re.finditer(r"^\t\(segment", self.t, re.M):
            b = C.sexp(self.t, m.start() + 1)
            s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
            w = re.search(r"\(width ([-\d.]+)\)", b)
            n = re.search(r"\(net (\d+)\)", b)
            l = re.search(r'\(layer "([^"]+)"\)', b)
            self.tracks.append(((float(s.group(1)), float(s.group(2))),
                                (float(e.group(1)), float(e.group(2))),
                                float(w.group(1)), l.group(1), int(n.group(1))))

    def has_copper(self, pd):
        """a track already terminates inside this pad"""
        for s, e, w, layer, nid in self.tracks:
            if layer != "F.Cu": continue
            for q in (s, e):
                if (abs(q[0] - pd["x"]) <= pd["w"] / 2 and
                        abs(q[1] - pd["y"]) <= pd["h"] / 2): return True
        return False

    def klass(self, net):
        h = {p["netclass"] for p in self.pats if fnmatch.fnmatchcase(net, p["pattern"])}
        return h.pop() if len(h) == 1 else "Default"

    def clear_of_everything(self, a, b, width, net, clr):
        """swept trace a->b of `width` on F.Cu against every other-net item.

        The requirement is NOT one number. U1 and U2 carry a footprint-level
        (clearance 0.15) override, added deliberately because HighCurrent's
        0.30 mm is stricter than a 0.5 mm-pitch QFN or a SOT-563 physically
        allows. Applying the netclass value everywhere declared these escapes
        impossible when the board's own rules permit them. Where a footprint
        overrides, that is what DRC enforces, so that is what is checked.

        Returns the margin against the applicable rule, so >= 0 means legal."""
        half = width / 2
        worst = (1e9, None)
        for ref, p, pd in self.pads:
            if not pd["net"] or pd["net"] == net: continue
            need = pd["clear"] or self.fp_clear.get(p["ref"], clr)
            d = seg_rect_dist(a, b, pad_rect(pd)) - half - need
            if d < worst[0]: worst = (d, f"{ref}-{pd['num']} ({pd['net']}, needs {need:.2f})")
        for s, e, w, layer, nid in self.tracks:
            if layer != "F.Cu" or nid == self.netid.get(net): continue
            d = seg_seg_dist(a, b, s, e) - half - w / 2 - clr
            if d < worst[0]: worst = (d, f"track net {nid} (needs {clr:.2f})")
        return worst[0] >= 0, worst


def outward(p, pd):
    """unit vector from the footprint centre to the pad, snapped to an axis"""
    dx, dy = pd["x"] - p["x"], pd["y"] - p["y"]
    return (math.copysign(1, dx), 0.0) if abs(dx) >= abs(dy) else (0.0, math.copysign(1, dy))


def group_key(p, pd, d):
    return (p["ref"], pd["net"], d)


def solve(D, groups, min_reach):
    """propose link + escape + wide stub for every group, at this minimum reach"""
    good, bad = [], []
    for (ref, net, d), members in groups.items():
        ux, uy = d
        pads = [m[1] for m in members]
        k, want, clr = members[0][2], members[0][3], members[0][4]
        pads.sort(key=lambda q: q["y"] if ux else q["x"])
        links = [((pads[i]["x"], pads[i]["y"]), (pads[i+1]["x"], pads[i+1]["y"]))
                 for i in range(len(pads) - 1)]
        if any(math.dist(a, b) > MAX_LINK_MM for a, b in links):
            bad.append((ref, net, "pads too far apart to tie")); continue
        lm = (1e9, None)
        for a, b in links:
            w = D.clear_of_everything(a, b, LINK_W, net, clr)[1]
            if w[0] < lm[0]: lm = w
        if links and lm[0] < 0:
            bad.append((ref, net, f"link blocked by {lm[1]}")); continue
        origin = (sum(q["x"] for q in pads) / len(pads),
                  sum(q["y"] for q in pads) / len(pads))
        target = min(min(q["w"], q["h"]) for q in pads) * len(pads)
        order = ([w for w in ESCAPE_WIDTHS if target <= w <= want] +
                 [w for w in reversed(ESCAPE_WIDTHS) if w < target])
        sol = None; near = (-1e9, None)
        for ew in order:
            L = max(STEP, min_reach)
            while L <= MAX_REACH:
                b = (origin[0] + ux * L, origin[1] + uy * L)
                ok1, w1 = D.clear_of_everything(origin, b, ew, net, clr)
                best2 = None
                for vx, vy in ((ux, uy), (-uy, ux), (uy, -ux)):
                    c = (b[0] + vx * WIDE_STUB_MM, b[1] + vy * WIDE_STUB_MM)
                    ok2, w2 = D.clear_of_everything(b, c, want, net, clr)
                    if best2 is None or w2[0] > best2[1][0]: best2 = (c, w2, ok2)
                c, w2, ok2 = best2
                m = min(w1[0], w2[0], lm[0] if links else 1e9)
                lim = w1[1] if w1[0] < w2[0] else w2[1]
                if m > near[0]: near = (m, lim)
                if ok1 and ok2:
                    sol = (ew, L, b, c, m, lim); break
                L += STEP
            if sol: break
        if not sol:
            bad.append((ref, net, f"escape blocked, best {near[0]:+.3f} by {near[1]}")); continue
        ew, L, b, c, m, lim = sol
        good.append((ref, net, pads, links, origin, b, c, ew, want, L, m, lim))
    return good, bad


def segments_of(D, good):
    out = []
    for ref, net, pads, links, origin, b, c, ew, want, L, m, lim in good:
        nid = D.netid[net]
        for (s, e, w) in ([(a2, b2, LINK_W) for a2, b2 in links] +
                          [(origin, b, ew), (b, c, want)]):
            out.append((s, e, w, nid))
    return out


def neighbours(D, good, report=False):
    """with the escapes treated as copper, can every other pad still get out?

    THE CHECK WHOSE ABSENCE CAUSED THE REGRESSION. Each escape was verified
    against the board as it stood and every one passed -- but they were never
    checked against the pins that still had to get out PAST them. The shipped
    version was legal by DRC and left U1's signal pins 0.025 mm of working room,
    which cost two more connections than the fanout gained."""
    saved = D.tracks
    D.tracks = list(D.tracks) + [(s, e, w, "F.Cu", nid) for s, e, w, nid in segments_of(D, good)]
    escaped = {(g[0], q["num"]) for g in good for q in g[2]}
    affected = {g[0] for g in good}
    squeezed, rows = [], []
    for ref, p, pd in D.pads:
        if ref not in affected or not pd["net"] or pd["net"] == "GND": continue
        if (ref, pd["num"]) in escaped or D.has_copper(pd): continue
        k = D.klass(pd["net"]); w = D.cls[k]["track_width"]; clr = D.cls[k]["clearance"]
        ux, uy = outward(p, pd); a = (pd["x"], pd["y"])
        best = (-9e9, None)
        for L in [x / 100 for x in range(20, 200, 5)]:
            ok, worst = D.clear_of_everything(a, (a[0]+ux*L, a[1]+uy*L), w, pd["net"], clr)
            if worst[0] > best[0]: best = worst
            if ok: break
        rows.append((ref, pd["num"], pd["net"], best[0]))
        if best[0] < NEIGHBOUR_SLACK - 1e-9: squeezed.append(f"{ref}-{pd['num']}")
    D.tracks = saved
    if report:
        print(f"\n  can the neighbours still get out? (need {NEIGHBOUR_SLACK:.2f} mm to spare)")
        for ref, num, net, mgn in rows:
            flag = "" if mgn >= NEIGHBOUR_SLACK - 1e-9 else "   <-- SQUEEZED"
            print(f"    {ref}-{num:<4}{net:<30}{mgn:8.3f}{flag}")
    return squeezed


def main():
    apply_ = "--apply" in sys.argv
    D = Design()

    targets, trivial, done = [], [], []
    for ref, p, pd in D.pads:
        if not pd["net"] or pd["net"] == "GND" or not pd["smd"]: continue
        k = D.klass(pd["net"]); want = D.cls[k]["track_width"]
        if want <= min(pd["w"], pd["h"]): continue
        if D.has_copper(pd):
            done.append((ref, pd)); continue
        ux, uy = outward(p, pd)
        a = (pd["x"], pd["y"])
        ok = False
        for vx, vy in ((ux, uy), (-uy, ux), (uy, -ux)):
            c = (a[0] + vx * (WIDE_STUB_MM + 0.4), a[1] + vy * (WIDE_STUB_MM + 0.4))
            if D.clear_of_everything(a, c, want, pd["net"], D.cls[k]["clearance"])[0]:
                ok = True; break
        (trivial if ok else targets).append((ref, p, pd, k, want, D.cls[k]["clearance"]))
    if done:
        print(f"  {len(done)} pads already escaped by hand, left alone:")
        print("    " + ", ".join("%s-%s" % (r, pd["num"]) for r, pd in
                                 sorted(done, key=lambda x: (x[0], x[1]["num"]))) + "\n")
    if trivial:
        print(f"  {len(trivial)} pads take the class width directly, no neck needed:")
        print("    " + ", ".join("%s-%s" % (r, pd["num"]) for r, _, pd, *_ in
                                 sorted(trivial, key=lambda x: (x[0], x[2]["num"]))) + "\n")

    groups = OrderedDict()
    for ref, p, pd, k, want, clr in targets:
        groups.setdefault(group_key(p, pd, outward(p, pd)), []).append((p, pd, k, want, clr))
    print(f"  {len(targets)} pads in {len(groups)} escape groups")

    # Retry with the widening pushed progressively further off the pad row until
    # nothing is squeezed. A solution that is merely legal is not good enough --
    # that is what shipped last time.
    good = bad = None
    for attempt in range(RETRIES):
        mr = MIN_REACH0 + attempt * RETRY_STEP
        good, bad = solve(D, groups, mr)
        sq = neighbours(D, good)
        if not sq and not bad:
            print(f"  settled at minimum reach {mr:.2f} mm after {attempt + 1} attempt(s)\n")
            break
        print(f"    reach {mr:.2f}: {len(bad)} blocked, squeezed {sq or 'none'}")
    else:
        print("\n  could not find a set that leaves the neighbours room")
        return 1

    print(f"  {'group':<22}{'link':>6}{'esc w':>7}{'reach':>7}{'wide':>7}{'margin':>9}  limiting")
    for ref, net, pads, links, origin, b, c, ew, want, L, m, lim in good:
        tag = f"{ref} {net} x{len(pads)}"
        print(f"  {tag:<22}{LINK_W if links else 0:6.2f}{ew:7.2f}{L:7.2f}{want:7.2f}{m:9.3f}  {lim}")
    for ref, net, why in bad:
        print(f"  {ref+' '+net:<22}  BLOCKED  {why}")
    neighbours(D, good, report=True)
    print(f"\n  {len(good)} groups verified, {len(bad)} blocked")
    if not apply_:
        print("\n  dry run -- pass --apply to write them into the board")
        return 1 if bad else 0

    out = []
    for s, e, w, nid in segments_of(D, good):
        out.append(f'\t(segment\n\t\t(start {s[0]:.4f} {s[1]:.4f})\n'
                   f'\t\t(end {e[0]:.4f} {e[1]:.4f})\n\t\t(width {w})\n'
                   f'\t\t(layer "F.Cu")\n\t\t(net {nid})\n'
                   f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
    t = D.t
    i = t.rfind("\n)")
    open(C.PCB, "w").write(t[:i] + "\n" + "".join(out).rstrip("\n") + t[i:])
    print(f"  wrote {len(out)} segments into {os.path.relpath(C.PCB)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
