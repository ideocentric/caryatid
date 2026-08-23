#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Centre five role labels on their connector's SILK OUTLINE, not its origin.

    python3 tools/oneshot/silk_centre_roles.py            # report
    python3 tools/oneshot/silk_centre_roles.py --apply

conn_labels places a role label at `p["x"]` -- the footprint's ORIGIN. For a
connector whose origin is pin 1 rather than the middle of the body, that is not
the centre of anything you can see, and the label reads as though it has slipped
sideways. All five here lean the same way, by between 0.38 and 0.58 mm:

    J1   DC IN         origin  57.317   silk centre  56.937   -0.380
    J3   LATCH         origin  57.658   silk centre  57.278   -0.380
    J4   CHG LEDS      origin  57.531   silk centre  57.151   -0.380
    J5   ANALOG BUS    origin 158.100   silk centre 157.525   -0.575
    J11  DIGITAL BUS   origin  59.950   silk centre  59.375   -0.575

The offset is the pin pitch's half-step: these are odd/even pin-count parts
whose origin sits on pin 1, so the body extends further one way than the other.

CENTRING IS THE ONE CASE WHERE P.tw's OVER-ESTIMATE COSTS NOTHING. The width
model returns KiCad's bounding box, about 1.1x the inked width plus a constant,
which is why right-justifying the audio jacks' pin labels had to hand alignment
back to KiCad. Here the surplus is split evenly on both sides of a centred
anchor, so it cancels: the drawn centre is the anchor regardless of the error.

y IS NOT TOUCHED. Only the horizontal position was wrong, and every one of these
labels sits on a vertical relationship with its connector that DRC has already
accepted.
"""
import sys, os, re, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import check_board as C
import pin_labels as P
import conn_labels as L

TARGET = ["J1", "J3", "J4", "J5", "J11"]
# Their reference designators are centred on the same outline, for the same
# reason -- J5's was hand-placed to "approximately centred" and landed 0.41 mm
# out, which is exactly the error a human eye cannot close and arithmetic can.
REF_CENTRE = ["J5", "J11"]
# Connectors the caller has already signed off at the bounding-box centre. They
# carry the same pin-1 chevron and are out by the same kind, but only 0.145 mm
# -- below what an eye can see, and moving ink that has been approved needs to
# be asked for rather than assumed. Empty means "centre everything in TARGET".
APPROVED_AS_IS = ["J1", "J3", "J4"]
CLEAR = 0.26
STROKE = 0.06        # half the silk stroke; silk geometry is centrelines


def silk_body(B, p, tol=0.02):
    """x-extent of the LARGEST CONNECTED silk outline on this footprint.

    NOT the bounding box of all its silk. J5 and J11 are IDC box headers, and
    each carries a pin-1 triangle standing OUTSIDE the body -- J5's occupies
    x 161.780..162.780 against a body ending at 161.390. Taking the union put
    the "centre" at 157.525 when the body, the pad span and the courtyard all
    independently agree on 156.830, and pushed the label 0.695 mm right. The
    marker is a separate closed shape, so grouping segments into connected
    components and keeping the biggest one drops it by construction, without a
    per-part exception list.

    J1, J3 and J4 have no such marker: their silk is one component, so this
    returns exactly what the bounding box did and they do not move.
    """
    segs = []
    for m in re.finditer(r"\(fp_(?:line|rect|poly|circle|arc)", p["blk"]):
        blk = C.sexp(p["blk"], m.start())
        if '"F.SilkS"' not in blk:
            continue
        pts = [B._xform(p, float(a), float(b)) for a, b in
               re.findall(r"\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)", blk)]
        if pts:
            segs.append(pts)
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if any(abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol
                   for a in segs[i] for b in segs[j]):
                parent[find(i)] = find(j)
    groups = {}
    for i, pts in enumerate(segs):
        groups.setdefault(find(i), []).extend(pts)

    def extent(g):
        xs = [q[0] for q in g]
        ys = [q[1] for q in g]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    best = max(groups.values(), key=extent)
    xs = [q[0] for q in best]
    ys = [q[1] for q in best]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    apply_ = "--apply" in sys.argv
    B = C.Board(C.PCB)
    t = B.t
    x0, y0, x1, y1 = B.outline
    u2r = {L.uid(r): r for r in L.LABELS}

    edits, boxes = [], []
    for m in re.finditer(r'^\t\(gr_text "([^"]*)"', t, re.M):
        blk = C.sexp(t, m.start() + 1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        if not u or u2r.get(u.group(1)) not in TARGET:
            continue
        ref = u2r[u.group(1)]
        if ref in APPROVED_AS_IS:
            continue
        p = [q for q in B.parts if q["ref"] == ref][0]
        sx, _, ex, _ = silk_body(B, p)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        sz = float(re.search(r'\(size ([\d.]+)', blk).group(1))
        rot = float(at.group(3) or 0)
        # A justified anchor is not the centre, so centring it would move the
        # ink somewhere other than where this computes. None of these carry one;
        # refuse rather than draw something the report does not describe.
        if "(justify" in blk:
            sys.exit(f"  {ref}: label is justified -- centring assumes a centred anchor")
        if rot % 180 != 0:
            sys.exit(f"  {ref}: label is rotated {rot:g} -- this centres along X only")
        ox, oy = float(at.group(1)), float(at.group(2))
        nx = (sx + ex) / 2
        w = P.tw(m.group(1), sz)
        up, dn = P.th_split(sz)
        boxes.append((f"{ref} {m.group(1)}", (nx - w / 2, oy - up, nx + w / 2, oy + dn)))
        new = blk[:at.start()] + f'(at {nx:.4f} {oy:.4f} {rot:g})' + blk[at.end():]
        edits.append((m.start() + 1, blk, new, ref, m.group(1), ox, nx,
                      (sx, ex), w))

    want = [r for r in TARGET if r not in APPROVED_AS_IS]
    if len(edits) != len(want):
        sys.exit(f"  found {len(edits)} of {len(want)} labels -- stopping")
    if APPROVED_AS_IS:
        print(f"  left alone at the caller's request: {', '.join(APPROVED_AS_IS)}")

    # reference designators, centred on the same outline
    fpedits = []
    for ref in REF_CENTRE:
        p = [q for q in B.parts if q["ref"] == ref][0]
        sx, _, ex, _ = silk_body(B, p)
        nx = (sx + ex) / 2
        rm = re.search(r'\(property "Reference" "[^"]+"', p["blk"])
        rblk = C.sexp(p["blk"], rm.start())
        ra = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', rblk)
        a = math.radians(p["rot"])
        cs, sn = math.cos(a), math.sin(a)
        lx0, ly0 = float(ra.group(1)), float(ra.group(2))
        ox = p["x"] + lx0 * cs + ly0 * sn
        oy = p["y"] - lx0 * sn + ly0 * cs
        dx, dy = nx - p["x"], oy - p["y"]
        lx, ly = dx * cs - dy * sn, dx * sn + dy * cs
        nrb = (rblk[:ra.start()]
               + f'(at {lx:.4f} {ly:.4f}{" " + ra.group(3) if ra.group(3) else ""})'
               + rblk[ra.end():])
        if t.count(p["blk"]) != 1:
            sys.exit(f"  {ref}: footprint block is not unique -- stopping")
        sz = float(re.search(r'\(size ([\d.]+)', rblk).group(1))
        w = P.tw(ref, sz)
        up, dn = P.th_split(sz)
        boxes.append((f"{ref} ref", (nx - w / 2, oy - up, nx + w / 2, oy + dn)))
        fpedits.append((t.index(p["blk"]) + rm.start(), rblk, nrb))
        print(f"  {ref:4} {'(reference)':12} x {ox:8.3f} -> {nx:8.3f} ({nx-ox:+.3f})")

    for _, _, _, ref, txt, ox, nx, (sx, ex), w in sorted(edits, key=lambda e: e[3]):
        print(f"  {ref:4} {txt:12} x {ox:8.3f} -> {nx:8.3f} ({nx-ox:+.3f})   "
              f"silk {sx:.2f}..{ex:.2f}, label spans {nx-w/2:.2f}..{nx+w/2:.2f}")

    # verify, all or nothing
    obst = P.Obstacles(B)
    for box, nm in P.surviving_labels(t):
        obst.add_label(box, nm)
    mine = {e[3] for e in edits}
    bad = []
    for nm, box in boxes:
        if (box[0] < x0 + 0.5 or box[2] > x1 - 0.5
                or box[1] < y0 + 0.5 or box[3] > y1 - 0.5):
            bad.append(f"{nm} runs into the board edge")
        h = obst.clash(box, CLEAR)
        # The obstacle set holds these labels at their OLD position; a hit that
        # names one of them, or names the connector it belongs to, is the thing
        # being moved rather than something it has run into.
        if h and not any(k in h for k in mine) and not any(k in h for k in
                                                           (nm.split()[1],)):
            bad.append(f"{nm} hits {h}")
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            (na, A), (nb, Bx) = boxes[a], boxes[b]
            g = max(max(A[0], Bx[0]) - min(A[2], Bx[2]),
                    max(A[1], Bx[1]) - min(A[3], Bx[3]))
            if g < CLEAR:
                bad.append(f"{na} vs {nb}: {g:+.3f} mm")
    if bad:
        for b in bad:
            print(f"  ! {b}")
        sys.exit(f"\n  {len(bad)} problem(s) -- nothing written")
    print(f"\n  {len(edits)} labels centred; 0 problems")

    # ONE MERGED PASS, STRICTLY BACK TO FRONT. Two separate descending passes --
    # footprint properties, then texts -- is NOT equivalent and corrupted the
    # board on the first attempt: every offset was measured against the same
    # original string, so the property pass shifted the file under the text
    # pass and `ANALOG BUS` was spliced inside another label's (effects) block.
    # Parenthesis balance survived it, which is exactly why the check below is
    # structural as well as arithmetic.
    todo = [(off, old, new) for off, old, new in fpedits]
    for off, old, new, *_ in edits:
        if "(locked yes)" not in new:
            head = new.index("\n") + 1
            new = new[:head] + "\t\t(locked yes)\n" + new[head:]
        todo.append((off, old, new))
    for off, old, new in sorted(todo, key=lambda e: -e[0]):
        if t[off:off + len(old)] != old:
            sys.exit(f"  offset {off} no longer holds what was measured -- not writing")
        t = t[:off] + new + t[off + len(old):]

    # STRUCTURAL CHECK. A splice can leave the parenthesis count untouched, so
    # count the blocks too: every gr_text must still start a top-level item.
    top = len(re.findall(r"^\t\(gr_text ", t, re.M))
    allt = t.count("(gr_text ")
    if top != allt:
        sys.exit(f"  {allt - top} gr_text no longer at top level -- not writing")
    if top != len(re.findall(r"^\t\(gr_text ", B.t, re.M)):
        sys.exit("  gr_text count changed -- not writing")

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
