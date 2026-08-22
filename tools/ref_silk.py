#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show component reference designators wherever one will fit.

    python3 tools/ref_silk.py            # report what would be placed
    python3 tools/ref_silk.py --apply
    python3 tools/ref_silk.py --hide-all --apply     # back to hidden

106 of 131 references are hidden. That is residue: the board was once
double-sided and "hide the back references" was a reasonable blanket rule.
Everything is on the front now, so the rule describes nothing, and a board you
cannot read during rework is worse than one with a few crowded labels.

WHAT STAYS HIDDEN, AND WHY
--------------------------
Not everything should come back:

  H1-H4    mounting holes -- mechanical, no part to identify
  FID1-3   fiducials -- read by a machine, and FID2's designator was landing
           on H4's mask opening, which is why it was hidden in the first place
  U2, L1, FB1, R61
           their labels collide with their own outlines and get clipped by
           solder mask, which puts ink on bare copper. R61 joined them after
           the audio re-placement: every spot this tool tried for it came back
           clipped, because the obstacle model checks pads and silk but not
           mask openings, so it placed a label the fab would print onto copper

Everything else is tried. A reference that cannot be placed clear of silk,
pads and its neighbours is LEFT HIDDEN rather than forced -- a designator
overlapping a pad is worse than no designator, because it prints ink on a
solderable surface.

SIZE
----
1.0 mm first, then 0.9, then 0.8. 0.8 is JLC's floor for text height and this
does not go below it. The board is dense around the audio section, so expect
the small sizes to do real work there.
"""
import sys, os, re, math, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C
import pin_labels as P

KEEP_HIDDEN = {"U2", "L1", "FB1", "R61"}
SKIP_PREFIX = ("H", "FID")
SIZES = (1.0, 0.9, 0.8)
THICK = 0.15
CLEAR = 0.26


def ref_box(cx, cy, text, size):
    w = P.tw(text, size)
    up, dn = P.th_split(size)
    return (cx - w/2, cy - up, cx + w/2, cy + dn)


def local(p, X, Y):
    """board position -> footprint-local offset, inverting check_board._xform"""
    a = math.radians(p["rot"]); cs, sn = math.cos(a), math.sin(a)
    dX, dY = X - p["x"], Y - p["y"]
    return (dX*cs - dY*sn, dX*sn + dY*cs)


def main():
    apply_ = "--apply" in sys.argv
    hide_all = "--hide-all" in sys.argv
    B = C.Board(C.PCB)
    t = B.t

    if hide_all:
        n = 0
        for m in list(re.finditer(r"^\t\(footprint ", t, re.M))[::-1]:
            blk = C.sexp(t, m.start()+1)
            rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
            if not rm: continue
            pb = C.sexp(blk, rm.start())
            if "(hide yes)" in pb: continue
            new = blk.replace(pb, pb[:-1] + "\t\t(hide yes)\n\t" + pb[-1], 1)
            t = t[:m.start()+1] + new + t[m.start()+1+len(blk):]
            n += 1
        print(f"  hid {n} references")
        if apply_: open(C.PCB, "w").write(t)
        else: print("  dry run -- pass --apply to write")
        return 0

    obst = P.Obstacles(B)
    for box, nm in P.surviving_labels(t): obst.add_label(box, nm)
    x0, y0, x1, y1 = B.outline

    cands = []
    for p in B.parts:
        rm = re.search(r'\(property "Reference" "([^"]+)"', p["blk"])
        if not rm: continue
        ref = rm.group(1)
        pb = C.sexp(p["blk"], rm.start())
        if "(hide yes)" not in pb: continue
        if ref in KEEP_HIDDEN or ref.startswith(SKIP_PREFIX): continue
        cands.append((p, ref))

    print(f"  {len(cands)} hidden references to try\n")
    placed, failed = [], []
    for p, ref in sorted(cands, key=lambda q: q[1]):
        cy_ = B.courtyard(p) or (p["x"]-1, p["y"]-1, p["x"]+1, p["y"]+1)
        got = None
        for size in SIZES:
            w = P.tw(ref, size); up, dn = P.th_split(size)
            h = up + dn
            for gap in (0.35, 0.55, 0.8, 1.1, 1.5):
                spots = [
                    (p["x"], cy_[1] - gap - up),                 # above
                    (p["x"], cy_[3] + gap + dn),                 # below
                    (cy_[0] - gap - w/2, p["y"]),                # left
                    (cy_[2] + gap + w/2, p["y"]),                # right
                ]
                for cx, cyy in spots:
                    box = ref_box(cx, cyy, ref, size)
                    if (box[0] < x0+0.5 or box[2] > x1-0.5
                            or box[1] < y0+0.5 or box[3] > y1-0.5): continue
                    if obst.clash(box, CLEAR): continue
                    got = (cx, cyy, size, box); break
                if got: break
            if got: break
        if got:
            cx, cyy, size, box = got
            placed.append((p, ref, cx, cyy, size))
            obst.add_label(box, f"ref {ref}")
        else:
            failed.append(ref)

    by_size = {}
    for _, _, _, _, s in placed: by_size[s] = by_size.get(s, 0) + 1
    print(f"  placed {len(placed)}   left hidden {len(failed)}")
    print(f"  sizes: " + ", ".join(f"{k} mm x{v}" for k, v in sorted(by_size.items(), reverse=True)))
    if failed:
        print(f"\n  no room, staying hidden ({len(failed)}):")
        for i in range(0, len(failed), 14):
            print("    " + " ".join(failed[i:i+14]))

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    # Board.parts carries no offset into the text, so locate each footprint by
    # its reference and edit back to front, or every earlier edit shifts the rest.
    want = {ref: (p, cx, cyy, size) for p, ref, cx, cyy, size in placed}
    spans = []
    for m in re.finditer(r"^\t\(footprint ", t, re.M):
        blk = C.sexp(t, m.start()+1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if rm and rm.group(1) in want:
            spans.append((m.start()+1, blk, rm.group(1)))
    for start, blk, ref in sorted(spans, key=lambda q: -q[0]):
        p, cx, cyy, size = want[ref]
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        pb = C.sexp(blk, rm.start())
        lx, ly = local(p, cx, cyy)
        new_pb = re.sub(r"\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?\)",
                        f"(at {lx:.4f} {ly:.4f} 0)", pb, count=1)
        new_pb = re.sub(r"\(size [\d.]+ [\d.]+\)", f"(size {size:g} {size:g})", new_pb, count=1)
        new_pb = re.sub(r"\n\s*\(hide yes\)", "", new_pb)
        new_blk = blk.replace(pb, new_pb, 1)
        t = t[:start] + new_blk + t[start+len(blk):]
    open(C.PCB, "w").write(t)
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"\n  shown {len(placed)} references, paren balance {d}")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())