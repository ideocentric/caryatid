#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild U1's exposed-pad thermal via array so paste cannot wick into it.

    python3 tools/fix_ep_thermal.py            # report
    python3 tools/fix_ep_thermal.py --apply

THE DEFECT
----------
Four PTH thermal vias sat at (+/-0.45, +/-0.45) inside a 1.68 x 1.68 mm EP,
with EP paste apertures printed directly on top of all four. The vias declare
(layers "*.Cu") and so open no mask themselves -- but that is not what decides
it. The EP pad declares F.Mask across the whole 1.68 mm square, and the vias
sit inside it, so every barrel was OPEN on the top face. The bottom face is
covered, because the B.Cu EP pad carries no B.Mask.

Open on top, sealed at the bottom, paste on top of the hole. That is a blind
cavity: paste wicks down it during reflow and the trapped air expands on the
way up. Both starve the joint.

WHY NOT JUST TENT THE FOUR
--------------------------
Because there is no pad left afterwards. Tenting needs a Ø0.90 mask disc per
via (Ø0.70 pad + 0.10 overlap); four of those cover 2.545 mm^2 of a 2.822 mm^2
EP and leave 10% solderable. The array as drawn is incompatible with an EP this
size unless the vias are resin-filled and capped, which is a fab option and a
cost. Two vias leave a real joint and need no fab option.

THE GEOMETRY, AND WHY IT IS THE SYMMETRIC ONE
---------------------------------------------
Measured over four candidate layouts, by grid integration rather than by eye:

    vias (0,+/-0.45), two vertical strips     42.9% of EP mask-open
    vias (+/-0.45,0), two horizontal strips   42.9%
    vias both on one side, one big block      50.0%
    vias on a diagonal, two quadrant blocks   44.2%

The one-sided layout wins on area and loses on reflow: a QFN's EP paste wants
to be symmetric so the part does not tilt as the paste collapses. 0.2 mm^2 is
not worth the skew, so this uses the symmetric pair.

Stencil aperture area ratio, the thing that decides whether paste releases:
0.28 x 1.60 mm on a 0.12 mm stencil gives 0.99, comfortably over the 0.66
floor. Paste is 74% of the mask opening, which is the ratio that matters for
float -- not the 32% of raw EP area, which is the wrong denominator once the
mask opening is smaller than the copper.

ALSO FIXED
----------
The paste apertures were DUPLICATED -- four unnumbered roundrect 0.69 pads
coincident with four numbered rect 0.72 pads. The stencil cuts the union, so
coverage was 73.5%, not the 67.5% the footprint description claimed.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

LIB = os.path.join(os.path.dirname(C.PCB), "caryatid.pretty",
                   "BQ24074RGT_QFN-16-1EP_3x3mm_P0.5mm.kicad_mod")
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

VIA_Y      = 0.45      # two vias on the vertical centreline
OPEN_X     = 0.66      # strip centres
OPEN_W     = 0.36      # strip width: starts at x 0.48, clear of the Ø0.90 tent
OPEN_H     = 1.68      # full EP height
PASTE_MARG = -0.04     # inset paste inside the mask opening

DESCR = ("TI BQ24074RGT, VQFN-16 (RGT) 3x3mm, 0.5mm pitch, 1.68mm exposed pad "
         "(TI nominal; 1.70 lands exactly on the 0.2mm clearance boundary). "
         "TWO thermal vias, 0.3mm drill on 0.70mm pads (0.20mm annular ring, "
         "JLC floor is 0.18), at (0,+/-0.45) on the EP centreline, MASK-TENTED "
         "on both faces. Four vias were tried and abandoned: tenting all four "
         "leaves 10% of the EP solderable. The EP mask opening is therefore "
         "NOT the full pad -- it is two 0.36x1.68 strips at x=+/-0.66 that "
         "clear the tents, 42.9% of the EP, with paste inset 0.04 to 74% of "
         "the opening. No paste lands on a barrel. Land pattern per SLUS810N "
         "RGT0016C drawing 4222419/E.")


def pad_blocks(t):
    out = []
    for m in re.finditer(r'\(pad "', t):
        blk = C.sexp(t, m.start())
        end = m.start() + len(blk)
        out.append((m.start(), end, blk))
    return out


def classify(blk):
    head = blk.split("\n")[0]
    at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
    x, y = (float(at.group(1)), float(at.group(2))) if at else (None, None)
    if "thru_hole" in head and abs(abs(x) - 0.45) < 1e-6 and abs(abs(y) - 0.45) < 1e-6:
        return "old_via"
    if '"F.Paste"' in blk and "F.Cu" not in blk:
        return "old_paste"
    if "1.68" in blk and '"F.Cu"' in blk and '"F.Mask"' in blk:
        return "ep_front"
    return "keep"


def build(is_board, net):
    """The replacement pads. The board copy needs net and uuid; the library
    must not have them."""
    def extra(tag):
        if not is_board: return ""
        u = uuid.uuid5(NS, f"caryatid-u1-ep-{tag}")
        return f'\n\t\t{net}\n\t\t(uuid "{u}")'
    out = []
    for i, sy in enumerate((-VIA_Y, VIA_Y)):
        out.append(
            f'(pad "17" thru_hole circle\n\t\t(at 0 {sy:g})\n\t\t(size 0.7 0.7)\n'
            f'\t\t(drill 0.3)\n\t\t(property pad_prop_heatsink)\n'
            f'\t\t(layers "*.Cu")\n\t\t(remove_unused_layers no){extra(f"via{i}")}\n\t)')
    for i, sx in enumerate((-OPEN_X, OPEN_X)):
        out.append(
            f'(pad "17" smd rect\n\t\t(at {sx:g} 0)\n\t\t(size {OPEN_W:g} {OPEN_H:g})\n'
            f'\t\t(property pad_prop_heatsink)\n'
            f'\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n'
            f'\t\t(solder_paste_margin {PASTE_MARG:g})\n'
            f'\t\t(zone_connect 2){extra(f"open{i}")}\n\t)')
    return out


def patch(t, is_board):
    blocks = pad_blocks(t)
    # The net must come from a pad NUMBERED 17. Taking "the first pad with a
    # net" grabs pad 1, which is /power/TS, and silently builds the whole
    # thermal pad on the temperature-sense net -- 6 shorts and 7 unconnected.
    net = ""
    for _, _, blk in blocks:
        if not blk.split("\n")[0].startswith('(pad "17"'): continue
        nm = re.search(r'\(net \d+ "[^"]*"\)', blk)
        if nm: net = nm.group(0); break
    if is_board and not net:
        raise SystemExit("  REFUSING: no net found on a pad numbered 17")
    drop, changed = [], 0
    for s, e, blk in blocks:
        k = classify(blk)
        if k in ("old_via", "old_paste"):
            e2 = e
            while e2 < len(t) and t[e2] in "\n\t":
                if t[e2] == "\n": e2 += 1; break
                e2 += 1
            drop.append((s, e2, k))
    counts = {}
    for _, _, k in drop: counts[k] = counts.get(k, 0) + 1

    # EP front pad: drop its mask layer so the copper stays and the opening moves
    for s, e, blk in blocks:
        if classify(blk) == "ep_front":
            new = blk.replace('(layers "F.Cu" "F.Mask")', '(layers "F.Cu")', 1)
            if new != blk:
                t = t[:s] + new + t[e:]
                changed += 1
            break

    blocks = pad_blocks(t)
    drop = []
    for s, e, blk in blocks:
        if classify(blk) in ("old_via", "old_paste"):
            e2 = e
            while e2 < len(t) and t[e2] in " \t": e2 += 1
            if e2 < len(t) and t[e2] == "\n": e2 += 1
            drop.append((s, e2))
    for s, e in sorted(drop, reverse=True):
        t = t[:s] + t[e:]

    anchor = max(m.start() for m in re.finditer(r'\(pad "', t))
    blk = C.sexp(t, anchor)
    at = anchor + len(blk)
    add = "".join("\n\t" + b for b in build(is_board, net))
    t = t[:at] + add + t[at:]
    return t, counts, changed


def report():
    B = C.Board(C.PCB)
    p = next(q for q in B.parts if q["ref"] == "U1")
    print(f"  U1 footprint rotation {p['rot']:g}  (local coords apply directly)"
          if p["rot"] == 0 else
          f"  WARNING: U1 is rotated {p['rot']:g}; check the result by eye")
    n_via = n_paste = 0
    for m in re.finditer(r'\(pad "', p["blk"]):
        k = classify(C.sexp(p["blk"], m.start()))
        n_via += k == "old_via"; n_paste += k == "old_paste"
    print(f"  currently: {n_via} thermal vias at (+/-0.45,+/-0.45), "
          f"{n_paste} paste-only apertures")
    print(f"  after:     2 vias at (0,+/-{VIA_Y:g}) mask-tented, "
          f"2 openings {OPEN_W:g}x{OPEN_H:g} at x=+/-{OPEN_X:g}")
    print(f"             mask-open {2*OPEN_W*OPEN_H:.4f} mm^2 = "
          f"{100*2*OPEN_W*OPEN_H/(1.68*1.68):.1f}% of EP")
    pw, ph = OPEN_W + 2*PASTE_MARG, OPEN_H + 2*PASTE_MARG
    print(f"             paste {2*pw*ph:.4f} mm^2 = {100*2*pw*ph/(2*OPEN_W*OPEN_H):.0f}% "
          f"of the opening, aperture area ratio "
          f"{(pw*ph)/(2*(pw+ph)*0.12):.2f} on a 0.12 mm stencil")


def main():
    apply_ = "--apply" in sys.argv
    report()
    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0
    for path, is_board in ((LIB, False), (C.PCB, True)):
        t = open(path).read()
        if is_board:
            m = re.search(r'\(property "Reference" "U1"', t)
            s = t.rindex("\n\t(footprint", 0, m.start()) + 1
            blk = C.sexp(t, s)
            new, counts, ch = patch(blk, True)
            new = re.sub(r'\(descr "(?:[^"\\]|\\.)*"\)', f'(descr "{DESCR}")', new, count=1)
            t = t[:s] + new + t[s+len(blk):]
        else:
            t, counts, ch = patch(t, False)
            t = re.sub(r'\(descr "(?:[^"\\]|\\.)*"\)', f'(descr "{DESCR}")', t, count=1)
        open(path, "w").write(t)
        d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
        print(f"  {os.path.basename(path):<34} removed {counts} , "
              f"mask-stripped {ch} , paren balance {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())