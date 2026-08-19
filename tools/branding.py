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

# (text, w, h, thickness, bold). absonus's wordmark is 3.556 x 2.54 bold,
# aspect 1.400. Here it is 3.2 x 2.286 -- the SAME aspect, 10% smaller -- and
# that reduction is forced, not stylistic: at 3.556 the ink is 20.32 mm wide and
# the only clear area able to hold the whole mark is 19 mm across. There is no
# 31 x 9 mm space anywhere on this board for a single-row icon-plus-name block,
# even with margins cut to 0.28 mm and the board-edge keepout to 0.6 mm.
NAME = ("caryatid",      3.2, 2.286, 0.20, True)
REV  = ("v0.1",          1.0, 1.0,   0.15, False)
LIC  = ("CERN-OHL-S v2", 1.0, 1.0,   0.15, False)

# CERN-OHL-S wants the Source reachable from the Product. The repository is
# public as of 2026-08-18, so the notice can carry a URL that resolves -- until
# then branding.py deliberately printed none, because a notice pointing at a
# 404 is worse than no notice. It does not fit beside the mark: at 1 mm the URL
# inks 24.34 mm against the mark block's 19 mm, so it goes along the bottom
# edge where 26 mm is clear.
URL     = ("github.com/ideocentric/caryatid", 1.0, 1.0, 0.15, False)
URL_AT  = (178.0, 116.0)
W_URL   = 24.34

# Measured ink, pcbnew GetEffectiveShape. The name's vertical extent about its
# anchor is NOT symmetric: -1.481 above, +2.024 below, because of the descender
# on the y. Treating it as +/-1.753 put the licence line 0.27 mm lower than
# intended relative to the ink and DRC reported 0.178 mm against a 0.25 rule.
W_NAME, H_NAME = 18.29, 3.51
NAME_UP, NAME_DN = 1.481, 2.024
W_REV,  W_LIC  = 2.96, 12.53
H_SMALL        = 1.15
SMALL_UP, SMALL_DN = 0.620, 0.530
LOGO_MM        = 9.0            # half the 18 mm it was; the icon's own size

# The largest clear silk area is 26 x 6 mm centred on (180,116), but the block
# is NOT centred in it. Centred, v0.1 lands at x 189.28..192.24 -- and the M3
# mounting hole at (195,115) puts a screw head there: a typical 5.5 mm head
# clears by 0.01 mm, a 6 mm head or any washer hides the revision marking
# completely. Nothing in DRC models a screw head; this was caught by rendering
# the silkscreen and looking at it. Shifted 2 mm left, which leaves 1.26 mm
# even against a 7 mm head with a washer.
CENTRE = (175.0, 55.5)          # the one clear 19 x 18 mm area on the board
GAP    = 1.50             # between the version and the licence, on their line


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


KNOWN = {str(uuid.uuid5(NS, f"caryatid-branding-{t}")) for t in ("name","rev","lic","url")}


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
    """Stacked: icon, then the name, then version and licence sharing a line.
    Returns the logo centre and the three text centres."""
    cx, cy = CENTRE
    top = cy - 9.0                       # top of the 18 mm tall area
    logo_cy = top + 0.5 + LOGO_MM / 2
    name_cy = logo_cy + LOGO_MM / 2 + 0.80 + NAME_UP
    # 1.375, SOLVED against KiCad's own glyph geometry, not derived from boxes.
    # Bounding boxes are useless for this pair: the licence string runs the full
    # width of the name and the binding distance is to the descender of the y,
    # between real outlines. Raising the vertical gap from 0.65 to 0.80 made DRC
    # WORSE (0.2145 -> 0.1960), which is the point at which modelling was
    # abandoned. Measured by binary-searching SHAPE.Collide against the placed
    # text -- true gap 0.052 at y 61.575, 0.196 at 61.725 (DRC agreed exactly),
    # 0.467 at 62.000, 0.766 at 62.300. This lands on 62.3.
    line_cy = name_cy + NAME_DN + 1.375 + SMALL_UP
    run = W_REV + GAP + W_LIC
    left = cx - run / 2
    return ((cx, logo_cy), (cx, name_cy),
            (left + W_REV / 2, line_cy),
            (left + W_REV + GAP + W_LIC / 2, line_cy))


def main():
    apply_ = "--apply" in sys.argv
    t = open(C.PCB).read()
    t, removed = strip(t)
    if removed: print(f"  removed {removed} existing branding text")

    if "--strip" in sys.argv:
        if apply_: open(C.PCB, "w").write(t)
        else: print("  dry run -- pass --apply to write")
        return 0

    (lgx, lgy), (nx, ny), (vx, vy), (cx_, cy_) = layout()
    print(f"  ens\u014d      {LOGO_MM:g} mm            centred ({lgx:.2f},{lgy:.2f})")
    print(f"  '{NAME[0]}'  {NAME[1]}x{NAME[2]} th {NAME[3]} bold  at ({nx:.2f},{ny:.2f})")
    print(f"  '{REV[0]}'      {REV[1]}x{REV[2]} th {REV[3]}       at ({vx:.2f},{vy:.2f})")
    print(f"  '{LIC[0]}' {LIC[1]}x{LIC[2]} th {LIC[3]}  at ({cx_:.2f},{cy_:.2f})")
    print(f"  '{URL[0]}' {URL[1]}x{URL[2]}  at ({URL_AT[0]:.2f},{URL_AT[1]:.2f})")

    # Clearance against everything, including the locked pin labels -- but
    # measured on the STRIPPED text, not the file. Reading the file here means
    # colliding with the branding this run is about to replace.
    import pin_labels as P
    B = C.Board.__new__(C.Board); C.Board.__init__(B, C.PCB)
    obst = P.Obstacles(B)
    for box, nm in P.surviving_labels(t): obst.add_label(box, nm)
    ok = True
    items = (((nx, ny), W_NAME, (NAME_UP, NAME_DN), NAME[0]),
             ((vx, vy), W_REV,  (SMALL_UP, SMALL_DN), REV[0]),
             ((cx_, cy_), W_LIC, (SMALL_UP, SMALL_DN), LIC[0]),
             ((lgx, lgy), LOGO_MM, (LOGO_MM/2, LOGO_MM/2), "ens\u014d"),
             (URL_AT, W_URL, (SMALL_UP, SMALL_DN), URL[0]))
    for (px, py), w, (u_, d_), lbl in items:
        box = (px - w/2, py - u_, px + w/2, py + d_)
        hit = obst.clash(box, 0.25)
        x0, y0, x1, y1 = B.outline
        edge = min(box[0]-x0, x1-box[2], box[1]-y0, y1-box[3])
        print(f"    {lbl:<14} {'CLASH with ' + hit if hit else 'clear':<28}"
              f" {edge:6.2f} mm to the board edge")
        ok &= hit is None and edge >= 0.30
    # and against each other
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            (ax, ay), aw, (au, ad), al = items[i]
            (bx, by), bw, (bu, bd), bl = items[j]
            g = P.rect_rect((ax-aw/2, ay-au, ax+aw/2, ay+ad),
                            (bx-bw/2, by-bu, bx+bw/2, by+bd))
            if g < 0.25:
                print(f"    {al} vs {bl}: only {g:.3f} mm apart"); ok = False
    if not ok:
        print("\n  REFUSING: placement is not clear")
        return 1
    if not apply_:
        print("\n  dry run -- pass --apply to write")
        print(f"  then: .venv/bin/python tools/svg_to_silk.py "
              f"--size {LOGO_MM:g} --at {lgx:.2f},{lgy:.2f} --apply")
        return 0

    at = t.rindex("\n)")
    t = (t[:at]
         + emit(NAME[0], nx, ny, NAME[1], NAME[2], NAME[3], NAME[4], "name")
         + emit(REV[0],  vx, vy, REV[1],  REV[2],  REV[3],  REV[4],  "rev")
         + emit(LIC[0],  cx_, cy_, LIC[1], LIC[2], LIC[3], LIC[4], "lic")
         + emit(URL[0], URL_AT[0], URL_AT[1], URL[1], URL[2], URL[3], URL[4], "url")
         + t[at:])
    open(C.PCB, "w").write(t)
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"\n  wrote 4 texts, paren balance {d}")
    print(f"  now: .venv/bin/python tools/svg_to_silk.py "
          f"--size {LOGO_MM:g} --at {lgx:.2f},{lgy:.2f} --apply")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())