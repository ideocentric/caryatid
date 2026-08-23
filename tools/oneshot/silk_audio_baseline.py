#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""J12's pin letters back onto their pads; the audio jacks onto a J19 baseline.

    python3 tools/oneshot/silk_audio_baseline.py            # report
    python3 tools/oneshot/silk_audio_baseline.py --apply

J12 -- WHY THE JUSTIFICATION HAD TO GO
---------------------------------------
silk_align_connectors put every connector's END pin labels out on the silk
outline, because that is what makes a crowded row readable: `5V 3V3 GND D11`
across a 12 mm body has no slack, so the ends anchor to the outline and the
inner labels stay on their pads.

Shortening RED/GRN/BLU to R/G/B removed the crowding, and with it the reason.
J12's four labels now measure 6.6 mm along a 12.9 mm body. Justifying `B` and
`5V` to the outline moved them 1.94 and 1.82 mm OFF the pins they name -- `B`
ended up nearer pin 5's position than pin 4's. The justification rule is a
crowding remedy, and applying it to an uncrowded row costs the one thing the
label is for. All four now sit on their pad centre.

J14 / J17 / J18 -- THE J19 PARADIGM, ROTATED
----------------------------------------------
J8 and J19 read: reference at one end, role at the other, both on ONE baseline
on the far side of the board from the pin labels. The audio jacks are rot 90
with their pins broken out to the left, so the far side is the right-hand strip
and the baseline is vertical.

Two things made this cheap. Their references are ALREADY rot 90 -- KiCad stores
footprint-text angle absolutely, and these read `(at 1.25 -3.55 90)` -- so this
is a move, not a re-orientation. And the strip between the silk outlines and the
board edge is empty: measured over x 197.05..198.30, y 44..86, `Obstacles.clash`
at zero clearance returns nothing.

    silk right EDGE   196.864     baseline x   197.800
    box @1.0          197.180 .. 198.330   -> 0.316 to silk, 1.670 to board edge
    box @0.8          197.287 .. 198.237

THE SILK BBOX IS CENTRELINES, NOT EDGES, and the first attempt at this forgot
it. `fp_line` coordinates are the middle of a 0.12 mm stroke, so J14's and
J18's outlines really end at 196.864, not 196.80. At x 197.700 the model
reported 0.280 mm clear and DRC reported 0.2158 -- twice, once per connector.
J17's outline ends 0.14 mm sooner and passed, which is exactly the kind of
near-miss that makes a bad model look like a good one. STROKE is now added
explicitly in the check below rather than absorbed into the baseline.

READING ORDER PUTS THE REFERENCE AT THE BOTTOM. rot 90 text reads upward, so
its first character is at MAX y. J19's reference is left-justified and its role
right-justified; rotated, that is reference at the bottom end, role at the top
-- which also leaves each role label on the side it already sat on.

J14 DOES NOT FIT AND IS CENTRED INSTEAD
-----------------------------------------
    J17   'J17' 2.92 + 'AUDIO OUT' 6.99 =  9.91  vs body 10.41   +0.50
    J18   'J18' 2.92 + 'AUDIO IN'  5.93 =  8.84  vs body 10.41   +1.57
    J14   'J14' 2.92 + 'MIC RTN'   5.51 =  8.42  vs body  7.91   -0.51

J14 is a 2-pin jack, so its body is 2.5 mm shorter than the 3-pin parts while
its role string is not. Rather than skip it -- the caller asked for all three,
and one unlabelled jack in a row of three reads as an oversight -- the pair is
CENTRED on the connector with the minimum gap and allowed to overrun the
outline by 0.44 mm at each end. That is only defensible because the space is
provably free: J18's silk ends 3.26 mm above, and nothing lies below.

Buying the fit by shrinking 'MIC RTN' below its neighbours' 0.8 mm was rejected
for the reason silk_align_connectors gives for J15 and J19 -- text that differs
in size from the labels beside it reads as a different KIND of label.

conn_labels OWNS THESE ROLE STRINGS BY UUID and re-derives their placement from
its own free-space search; a plain `conn_labels.py --apply` will move them back,
exactly as `pin_labels.py --apply` reverts silk_align_connectors. The locks stop
an accident, not a deliberate re-run.
"""
import sys, os, re, uuid, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import check_board as C
import pin_labels as P
import conn_labels as L

BASE_X = 197.800     # vertical baseline in the empty right-hand strip
STROKE = 0.06        # half the 0.12 mm silk stroke -- silk_bbox is centrelines
GAP = 0.35           # minimum between reference and role when centred
CLEAR = 0.26         # board silk clearance 0.25 plus a working margin
EDGE = 0.50          # keep-out from the board outline
LEFT_GAP = 0.874     # pin label right edge to the jack outline; see below
AUDIO = ["J14", "J17", "J18"]

# Hand placement that this script must REPRODUCE, not overwrite. `MIC RTN` was
# moved off the flush-top rule by the board's author, who found the result still
# read wrong on J14 -- the shortest jack, where a top-flush label leaves a
# lopsided gap at the bottom. Recording it here is what keeps a re-run from
# quietly reverting a deliberate decision; the alternative is a script that
# fights its user every time it runs.
ROLE_OVERRIDE = {"J14": (197.880, 75.720)}
REF_OVERRIDE = {"J14": (197.840, 80.410)}


def ensure_justify(blk, how):
    """add (justify <how>) inside the effects block if it is not already there"""
    if "(justify" in blk:
        return blk
    m = re.search(r"\(effects", blk)
    if not m:
        return blk
    eff = C.sexp(blk, m.start())
    end = m.start() + len(eff)
    ins = eff.rstrip()[:-1].rstrip() + "\n\t\t\t(justify " + how + ")\n\t\t)"
    return blk[:m.start()] + ins + blk[end:]


def silk_bbox(B, p):
    pts = []
    for m in re.finditer(r"\(fp_(?:line|rect|poly|circle|arc)", p["blk"]):
        blk = C.sexp(p["blk"], m.start())
        if '"F.SilkS"' not in blk:
            continue
        for a, b in re.findall(r"\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)", blk):
            pts.append(B._xform(p, float(a), float(b)))
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


def to_local(p, X, Y):
    """board -> footprint-local, the inverse of check_board._xform"""
    a = math.radians(p["rot"])
    cs, sn = math.cos(a), math.sin(a)
    dx, dy = X - p["x"], Y - p["y"]
    return dx * cs - dy * sn, dx * sn + dy * cs


def main():
    apply_ = "--apply" in sys.argv
    B = C.Board(C.PCB)
    t = B.t
    x0, y0, x1, y1 = B.outline

    # ---- who owns which uuid -------------------------------------------
    owner, padpos = {}, {}
    for p in B.parts:
        m = re.search(r'\(property "Reference" "(J\d+)"', p["blk"])
        if not m:
            continue
        for pd in B.pads(p):
            owner[str(uuid.uuid5(P.NS, f"caryatid-pinlabel-{m.group(1)}-{pd['num']}"))] = \
                (m.group(1), pd["num"])
            padpos[(m.group(1), pd["num"])] = (pd["x"], pd["y"])
    role = {L.uid(r): r for r in L.LABELS}

    edits = []       # (start_of_block, old_block, new_block, describe)
    boxes = []       # (name, box) for everything this script draws

    # ---- 1. J12: every pin letter back onto its pad ---------------------
    for m in re.finditer(r'^\t\(gr_text "([^"]*)"', t, re.M):
        blk = C.sexp(t, m.start() + 1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        if not u or owner.get(u.group(1), ("", ""))[0] != "J12":
            continue
        ref, pin = owner[u.group(1)]
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        sz = float(re.search(r'\(size ([\d.]+)', blk).group(1))
        ox, oy = float(at.group(1)), float(at.group(2))
        nx = padpos[(ref, pin)][0]
        up, dn = P.th_split(sz)
        hw = P.tw(m.group(1), sz) / 2
        boxes.append((f"J12 {m.group(1)}", (nx - hw, oy - up, nx + hw, oy + dn)))
        if abs(nx - ox) < 1e-6 and "(locked yes)" in blk:
            continue
        new = blk[:at.start()] + f'(at {nx:.4f} {oy:.4f} {float(at.group(3) or 0):g})' + blk[at.end():]
        edits.append((m.start() + 1, blk, new,
                      f"  J12 pin{pin} {m.group(1):3} x {ox:8.3f} -> {nx:8.3f}  (pad centre)"))

    # ---- 2. audio jacks: reference + role onto one vertical baseline ----
    for ref in AUDIO:
        p = [q for q in B.parts if q["ref"] == ref][0]
        sl, lo, sr, hi = silk_bbox(B, p)
        rm = re.search(r'\(property "Reference" "[^"]+"', p["blk"])
        rblk = C.sexp(p["blk"], rm.start())
        rsz = float(re.search(r'\(size ([\d.]+)', rblk).group(1))
        w_ref = P.tw(ref, rsz)
        w_lab = P.tw(L.LABELS[ref], L.SIZE)

        # THE ROLE LABEL IS ALWAYS FLUSH WITH THE TOP OF ITS JACK. Centring the
        # pair when it does not fit -- the first rule here -- split the overrun
        # evenly and pushed `MIC RTN` 1.735 mm clear of J14's outline, which
        # reads as a label belonging to nothing. Three jacks in a column are
        # compared against each other, so the shared top edge is the alignment
        # that is actually visible; the reference simply runs on past the
        # bottom, into space that is measured free below.
        y_lab = lo + w_lab / 2
        base_x = BASE_X
        if ref in ROLE_OVERRIDE:
            base_x, y_lab = ROLE_OVERRIDE[ref]
        if w_ref + w_lab + CLEAR <= hi - lo:
            y_ref = hi - w_ref / 2                    # reads first, at the bottom
            how = "justified to the outline"
        else:
            y_ref = y_lab + w_lab / 2 + GAP + w_ref / 2
            how = (f"role flush at the top, reference overruns the bottom by "
                   f"{y_ref + w_ref / 2 - hi:.2f} mm")

        ref_x = BASE_X
        if ref in REF_OVERRIDE:
            ref_x, y_ref = REF_OVERRIDE[ref]
        for nm, sz, w, yy, xx, is_ref in ((ref, rsz, w_ref, y_ref,
                                           REF_OVERRIDE.get(ref, (BASE_X,))[0], True),
                                          (L.LABELS[ref], L.SIZE, w_lab, y_lab, base_x, False)):
            up, dn = P.th_split(sz)
            boxes.append((f"{ref} {'ref' if is_ref else 'role'}",
                          (xx - up, yy - w / 2, xx + dn, yy + w / 2)))
        print(f"  {ref:4} body {lo:.2f}..{hi:.2f} ({hi-lo:.2f} mm), "
              f"text {w_ref + w_lab:.2f} mm -- {how}")

        # reference: a footprint property, so write it in local coordinates
        lx, ly = to_local(p, ref_x, y_ref)
        rat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', rblk)
        nrb = rblk[:rat.start()] + f'(at {lx:.4f} {ly:.4f} 90)' + rblk[rat.end():]
        # check_board's parts carry the block text, not its offset. The block
        # contains the footprint's own uuid, so it is unique in the file --
        # assert that rather than trusting it.
        if t.count(p["blk"]) != 1:
            sys.exit(f"  {ref}: footprint block is not unique -- stopping")
        edits.append((t.index(p["blk"]) + rm.start(), rblk, nrb,
                      f"        {ref:9} ref  -> ({ref_x:.3f},{y_ref:7.3f}) rot 90"
                      + ("  [override]" if ref in REF_OVERRIDE else "")))

        # LEFT-HAND PIN LABELS: right-justified to a common edge beside the
        # jack. They were centred on one shared x, so the widest (GND, RTN)
        # sat nearly flush at 190.05..190.19 while the single letters L and R
        # floated 1.1 mm further out -- a ragged left edge that read as three
        # different distances from the same connector.
        right = sl - STROKE - LEFT_GAP
        for m in re.finditer(r'^\t\(gr_text "([^"]*)"', t, re.M):
            blk = C.sexp(t, m.start() + 1)
            u = re.search(r'\(uuid "([^"]+)"\)', blk)
            if not u or owner.get(u.group(1), ("", ""))[0] != ref:
                continue
            pin = owner[u.group(1)][1]
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
            sz = float(re.search(r'\(size ([\d.]+)', blk).group(1))
            ox, oy = float(at.group(1)), float(at.group(2))
            w = P.tw(m.group(1), sz)
            # THE ANCHOR IS THE RIGHT EDGE, because these carry (justify right).
            # Centring them on `right - w/2` is what made them ragged: P.tw is
            # KiCad's BOUNDING box, about 1.1x the inked width plus a constant,
            # so half of that surplus lands on each side and a 3-character label
            # indents ~0.11 mm further than a 1-character one. Right-justifying
            # hands the alignment to KiCad and the model error stops mattering:
            # it now only extends the box leftward, which is the safe direction.
            nx = right
            up, dn = P.th_split(sz)
            boxes.append((f"{ref} pin{pin}", (nx - w, oy - up, nx, oy + dn)))
            new = ensure_justify(blk, "right")
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', new)
            new = new[:at.start()] + f'(at {nx:.4f} {oy:.4f} 0)' + new[at.end():]
            if new == blk and "(locked yes)" in blk:
                continue
            edits.append((m.start() + 1, blk, new,
                          f"        {ref} pin{pin} {m.group(1):3} x {ox:8.3f} -> {nx:8.3f}"
                          f"  (right edge)"))

        # role label: a board-level gr_text placed by conn_labels
        hit = None
        for m in re.finditer(r'^\t\(gr_text "([^"]*)"', t, re.M):
            blk = C.sexp(t, m.start() + 1)
            u = re.search(r'\(uuid "([^"]+)"\)', blk)
            if u and role.get(u.group(1)) == ref:
                hit = (m.start() + 1, blk)
                break
        if not hit:
            sys.exit(f"  {ref}: no conn_labels text found -- stopping")
        s, blk = hit
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        new = blk[:at.start()] + f'(at {base_x:.4f} {y_lab:.4f} 90)' + blk[at.end():]
        if not (new == blk and "(locked yes)" in blk):
            edits.append((s, blk, new,
                          f"        {L.LABELS[ref]:9} role -> ({base_x:.3f},{y_lab:7.3f}) rot 90"
                          + ("  [override]" if ref in ROLE_OVERRIDE else "")))

    for _, _, _, d in edits:
        if d.startswith("  J12"):
            print(d)
    for _, _, _, d in edits:
        if not d.startswith("  J12"):
            print(d)

    # ---- verify BEFORE writing, all or nothing -------------------------
    # The obstacle model carries these items at their OLD positions, so a hit
    # naming something this script moves is its own ghost, not a collision.
    obst = P.Obstacles(B)
    mine = {n.split()[0] for n, _ in boxes}
    bad = []
    # Against the jack's own outline, PER SIDE. The reference and role sit to
    # the right of it and the pin labels to the left, so one comparison cannot
    # serve both -- scoring the pin labels against the right edge reported them
    # 9.7 mm "inside" a part they are nowhere near.
    for ref in AUDIO:
        p = [q for q in B.parts if q["ref"] == ref][0]
        sl, _, sr, _ = silk_bbox(B, p)
        for nm, box in boxes:
            if not nm.startswith(ref + " "):
                continue
            if nm.endswith((" ref", " role")):
                g = box[0] - (sr + STROKE)
            else:
                g = (sl - STROKE) - box[2]   # == LEFT_GAP by construction
            if g < CLEAR - 1e-6:
                bad.append(f"{nm} is {g:+.3f} mm from {ref}'s own outline")
    for nm, box in boxes:
        if (box[0] < x0 + EDGE or box[2] > x1 - EDGE
                or box[1] < y0 + EDGE or box[3] > y1 - EDGE):
            bad.append(f"{nm} runs into the board edge")
        h = obst.clash(box, CLEAR)
        if h and h.split()[0] not in mine and not any(k in h for k in mine):
            bad.append(f"{nm} hits {h}")
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            (na, A), (nb, Bx) = boxes[a], boxes[b]
            gx = max(A[0], Bx[0]) - min(A[2], Bx[2])
            gy = max(A[1], Bx[1]) - min(A[3], Bx[3])
            if max(gx, gy) < CLEAR:
                bad.append(f"{na} vs {nb}: {max(gx, gy):+.3f} mm")
    if bad:
        for b in bad:
            print(f"  ! {b}")
        sys.exit(f"\n  {len(bad)} problem(s) -- nothing written")
    print(f"\n  {len(edits)} edits, {len(boxes)} boxes checked; 0 problems")

    # write back to front so earlier offsets stay valid
    for s, old, new, _ in sorted(edits, key=lambda e: -e[0]):
        if "(locked yes)" not in new and new.lstrip().startswith("(gr_text"):
            head = new.index("\n") + 1
            new = new[:head] + "\t\t(locked yes)\n" + new[head:]
        t = t[:s] + new + t[s + len(old):]

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