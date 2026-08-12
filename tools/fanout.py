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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board as C

JLC_MIN_TRACK = 0.10
NECK_CHOICES  = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10)   # widest that fits wins
WIDE_STUB_MM  = 0.60      # length of class-width copper proved at the far end
STEP          = 0.05
MAX_REACH     = 4.0


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


def main():
    apply_ = "--apply" in sys.argv
    D = Design()

    # A pad needs an escape only if the class-width trace cannot leave it
    # DIRECTLY. "Track wider than the pad" is not the test -- a 1.20 mm trace off
    # a 1.00 mm pad with nothing beside it is fine, and necking it would add
    # clutter and two more joints for no reason. What matters is whether the wide
    # copper clears the neighbours.
    targets, trivial, done = [], [], []
    for ref, p, pd in D.pads:
        if not pd["net"] or pd["net"] == "GND" or not pd["smd"]: continue
        k = D.klass(pd["net"]); want = D.cls[k]["track_width"]
        if want <= min(pd["w"], pd["h"]): continue
        # Already escaped by hand -- U2 and C4 carry the boost loop, routed and
        # measured earlier. Adding a second escape to the same pad would be
        # duplicate copper, and re-running --apply would keep piling it on.
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
        print("    " + ", ".join(f"{r}-{pd['num']}" for r, pd in
                                 sorted(done, key=lambda x: (x[0], x[1]["num"]))) + "\n")
    if trivial:
        print(f"  {len(trivial)} pads take the class width directly, no neck needed:")
        print("    " + ", ".join(f"{r}-{pd['num']}" for r, _, pd, *_ in
                                 sorted(trivial, key=lambda x: (x[0], x[2]["num"]))) + "\n")

    print(f"  {len(targets)} fine-pitch pads to escape\n")
    print(f"  {'pad':<9}{'net':<11}{'neck':>6}{'reach':>7}{'wide':>7}   {'margin':>7}  limiting")
    good, bad = [], []
    for ref, p, pd, k, want, clr in sorted(targets, key=lambda x: (x[0], x[2]["num"])):
        ux, uy = outward(p, pd)
        a = (pd["x"], pd["y"])
        sol = None; near = (-1e9, None, None)   # best near-miss, for diagnosis
        for neck in NECK_CHOICES:
            if neck < JLC_MIN_TRACK: continue
            L = STEP
            while L <= MAX_REACH:
                b = (a[0] + ux * L, a[1] + uy * L)
                ok1, w1 = D.clear_of_everything(a, b, neck, pd["net"], clr)
                # The wide copper does not have to continue straight. Going only
                # straight out declared U1-10/11 impossible because D1 sits in
                # that direction -- but a human would turn, so try turning.
                best2 = None
                for vx, vy in ((ux, uy), (-uy, ux), (uy, -ux)):
                    c = (b[0] + vx * WIDE_STUB_MM, b[1] + vy * WIDE_STUB_MM)
                    ok2, w2 = D.clear_of_everything(b, c, want, pd["net"], clr)
                    if best2 is None or w2[0] > best2[1][0]: best2 = (c, w2, ok2)
                c, w2, ok2 = best2
                m = min(w1[0], w2[0]); lim = w1[1] if w1[0] < w2[0] else w2[1]
                if m > near[0]: near = (m, lim, f"neck {neck} reach {L:.2f}")
                if ok1 and ok2:
                    sol = (neck, L, b, c, m, lim)
                    break
                L += STEP
            if sol: break
        if sol:
            neck, L, b, c, margin, lim = sol
            good.append((ref, pd, neck, a, b, c, want))
            print(f"  {ref+'-'+pd['num']:<9}{pd['net']:<11}{neck:6.2f}{L:7.2f}{want:7.2f}   {margin:7.3f}  {lim}")
        else:
            bad.append((ref, pd, near))
            print(f"  {ref+'-'+pd['num']:<9}{pd['net']:<11}     --  blocked, best "
                  f"{near[0]:+.3f} vs {clr:.2f} needed by {near[1]} @ {near[2]}")

    print(f"\n  {len(good)} escapes verified, {len(bad)} impossible")
    if bad:
        print("  impossible:", ", ".join(f"{r}-{pd['num']}" for r, pd, _ in bad))
    if not apply_:
        print("\n  dry run -- pass --apply to write them into the board")
        return 1 if bad else 0

    out = []
    for ref, pd, neck, a, b, c, want in good:
        nid = D.netid[pd["net"]]
        for (s, e, w) in ((a, b, neck), (b, c, want)):
            out.append(f'\t(segment\n\t\t(start {s[0]:.4f} {s[1]:.4f})\n'
                       f'\t\t(end {e[0]:.4f} {e[1]:.4f})\n\t\t(width {w})\n'
                       f'\t\t(layer "F.Cu")\n\t\t(net {nid})\n'
                       f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
    t = D.t
    i = t.rfind("\n)")
    t = t[:i] + "\n" + "".join(out).rstrip("\n") + t[i:]
    open(C.PCB, "w").write(t)
    print(f"  wrote {len(out)} segments into {os.path.relpath(C.PCB)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())