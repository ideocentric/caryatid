#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Place the board name and revision on the silkscreen.

    python3 tools/branding.py              # report placement and clearance
    python3 tools/branding.py --apply
    python3 tools/branding.py --strip --apply

STYLE COMES FROM absonus, CONTENT DOES NOT
------------------------------------------
absonus set the house style and it is followed exactly: 3.556 x 2.54 mm at
0.20 thickness, bold, on F.SilkS. There is no artwork to import -- absonus's
branding is plain KiCad stroke text in the built-in font, and that board
contains zero image objects. Nothing to convert, no font file, no bitmap.

What is NOT inherited is absonus's 90-degree rotation. That was a placement
decision for a tall board; this one has its clear space on a wide bottom edge,
so the text runs horizontally.

'caryatid' is 20.32 x 3.89 mm inked -- taller than absonus's 21.00 x 3.05
despite the same size, because of the descender on the y. Worth knowing before
assuming a slot that fits one fits the other.

THE VERSION IS AN INFERENCE
---------------------------
v0.1 is not sourced from anything. The repo has no version tag (only
snapshot/* restore points), no title block, and no version in the docs. It is
the obvious label for a first spin, and it is recorded here so that nobody
later reads it as having come from somewhere.

WHAT IS DELIBERATELY ABSENT
---------------------------
No licence line. ADR 0006 is explicit that the licence is still open --
"Partly settled. Derivation answered; licence still open" -- and there is no
LICENSE file in the repo. Silkscreening a licence would settle by accident a
decision that has not been taken. If CERN-OHL-S is adopted it will want a
notice on the product, and that is a deliberate later edit.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# (text, size, thickness, bold) -- absonus's exact style for the name
NAME = ("caryatid", 3.556, 2.54, 0.20, True)
REV  = ("v0.1",     1.0,   1.0,  0.15, False)

# The largest clear silk area is 26 x 6 mm centred on (180,116), but the block
# is NOT centred in it. Centred, v0.1 lands at x 189.28..192.24 -- and the M3
# mounting hole at (195,115) puts a screw head there: a typical 5.5 mm head
# clears by 0.01 mm, a 6 mm head or any washer hides the revision marking
# completely. Nothing in DRC models a screw head; this was caught by rendering
# the silkscreen and looking at it. Shifted 2 mm left, which leaves 1.26 mm
# even against a 7 mm head with a washer.
CENTRE = (178.0, 116.0)
GAP    = 1.20             # between the name and the revision
W_NAME, W_REV = 20.32, 2.96    # measured ink widths, pcbnew GetEffectiveShape


def emit(text, cx, cy, w, h, th, bold, tag):
    u = uuid.uuid5(NS, f"caryatid-branding-{tag}")
    b = "\n\t\t\t\t(bold yes)" if bold else ""
    return (f'\n\t(gr_text "{text}"\n'
            f'\t\t(at {cx:.4f} {cy:.4f})\n'
            f'\t\t(layer "F.SilkS")\n'
            f'\t\t(uuid "{u}")\n'
            f'\t\t(effects\n\t\t\t(font\n'
            f'\t\t\t\t(size {w:g} {h:g})\n'
            f'\t\t\t\t(thickness {th:g}){b}\n'
            f'\t\t\t)\n\t\t)\n\t)')


KNOWN = {str(uuid.uuid5(NS, f"caryatid-branding-{t}")) for t in ("name", "rev")}


def strip(t):
    n = 0
    while True:
        hit = None
        for m in re.finditer(r"^\t\(gr_text ", t, re.M):
            blk = C.sexp(t, m.start() + 1)
            u = re.search(r'\(uuid "([^"]+)"\)', blk)
            if u and u.group(1) in KNOWN:
                if "(locked yes)" in blk: continue
                e = m.start() + 1 + len(blk)
                while e < len(t) and t[e] == "\n": e += 1
                hit = (m.start(), e); break
        if not hit: return t, n
        t = t[:hit[0]] + t[hit[1]:]; n += 1


def layout():
    total = W_NAME + GAP + W_REV
    left = CENTRE[0] - total / 2
    return ((left + W_NAME / 2, CENTRE[1]),
            (left + W_NAME + GAP + W_REV / 2, CENTRE[1]))


def main():
    apply_ = "--apply" in sys.argv
    t = open(C.PCB).read()
    t, removed = strip(t)
    if removed: print(f"  removed {removed} existing branding text")

    if "--strip" in sys.argv:
        if apply_: open(C.PCB, "w").write(t)
        else: print("  dry run -- pass --apply to write")
        return 0

    (nx, ny), (vx, vy) = layout()
    total = W_NAME + GAP + W_REV
    print(f"  '{NAME[0]}'  {NAME[1]}x{NAME[2]} th {NAME[3]}"
          f"{' bold' if NAME[4] else ''}   at ({nx:.2f},{ny:.2f})")
    print(f"  '{REV[0]}'      {REV[1]}x{REV[2]} th {REV[3]}"
          f"          at ({vx:.2f},{vy:.2f})")
    print(f"  block {total:.2f} mm wide in a 26.0 mm clear area, centred on "
          f"({CENTRE[0]:g},{CENTRE[1]:g})")

    # Clearance against everything, including the locked pin labels -- but
    # measured on the STRIPPED text, not the file. Reading the file here means
    # colliding with the branding this run is about to replace, which is what
    # happened the first time and produced "CLASH with locked 'caryatid'".
    import pin_labels as P
    B = C.Board.__new__(C.Board); C.Board.__init__(B, C.PCB)
    obst = P.Obstacles(B)
    for box, nm in P.surviving_labels(t): obst.add_label(box, nm)
    ok = True
    for (cx, cy), w, h, lbl in (((nx, ny), W_NAME, 3.89, NAME[0]),
                                ((vx, vy), W_REV, 1.15, REV[0])):
        box = (cx - w/2, cy - h/2, cx + w/2, cy + h/2)
        hit = obst.clash(box, 0.25)
        x0, y0, x1, y1 = B.outline
        edge = min(box[0]-x0, x1-box[2], box[1]-y0, y1-box[3])
        print(f"    {lbl:<9} clearance {'CLASH with ' + hit if hit else 'clear'}"
              f", {edge:.2f} mm to the board edge")
        ok &= hit is None and edge >= 0.30
    if not ok:
        print("\n  REFUSING: placement is not clear")
        return 1
    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    at = t.rindex("\n)")
    t = (t[:at]
         + emit(NAME[0], nx, ny, NAME[1], NAME[2], NAME[3], NAME[4], "name")
         + emit(REV[0],  vx, vy, REV[1],  REV[2],  REV[3],  REV[4],  "rev")
         + t[at:])
    open(C.PCB, "w").write(t)
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"\n  wrote 2 texts, paren balance {d}")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())