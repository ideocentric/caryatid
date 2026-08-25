#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Find the things that make a schematic look generated rather than drawn.

    python3 tools/check_schematic.py            # report
    python3 tools/check_schematic.py --strict   # exit nonzero on any finding

IT REPORTS AND NEVER EDITS, and that is the whole design.
Moving a label to clear a symbol usually creates a new collision somewhere else,
and a schematic's readability depends on grouping and flow that no script can
see. Every finding here is a thirty-second fix in Eeschema once someone knows it
is there; the expensive part was never the fix, it was noticing.

WHAT IT DOES NOT CHECK, DELIBERATELY
------------------------------------
**Distance from a value to its symbol.** This was the first thing tried, and it
was worse than useless. It reported 220 of 272 texts as "more than 10 mm from
their symbol", which sounds alarming and describes a perfectly tidy schematic: a
reference designator 10 mm above a resistor is CORRECT placement, not drift.
A check that fires on healthy work trains people to ignore it.

**Whether the page is well used.** The audio sheet has a dense left side and an
empty middle-right, which is a real criticism and an unfixable one by machine.
Judging what belongs near what is the part a person does.

WHAT IT CHECKS, AND WHY EACH EARNED ITS PLACE
----------------------------------------------
1. SYMBOLS OUTSIDE THE DRAWING BORDER. Anything within 10 mm of the paper edge
   is under the frame KiCad prints, and plots clipped or overlapping the rule.

2. SYMBOLS INSIDE THE TITLE BLOCK. Found JP6 on audio.kicad_sch at
   (480.06, 391.16), its pin labels sitting across "File: audio.kicad_sch". The
   title block is roughly the bottom-right 110 x 32 mm and nothing else belongs
   there. This is the check that pays for the file.

3. LABELS CROSSING OR NEARLY TOUCHING A SYMBOL BODY.
   **This check exists because I twice claimed it was failing when it was not.**
   Looking at a 100 dpi plot, then a 300 dpi one, vertical net labels appeared to
   run through the resistors they name. The geometry disagrees: on
   audio.kicad_sch, R51's body ends at y 132.08 and BIAS_E_L's text begins at
   132.67. They clear by 0.59 mm. At plot scale a sub-millimetre gap reads as
   contact, which is a real cosmetic complaint and not a collision.
   So the check reports both, separately: OVERLAP is a defect, NEAR is
   0.6 mm or less of clearance and is cosmetic. Naming the difference is the
   point, because an eye cannot measure and a plot cannot be trusted to.

4. OVERLAPPING TEXT. Two visible texts whose boxes intersect. Text height is
   known exactly from the file; width is estimated, so this one is advisory and
   says so.

THE LIB_SYMBOLS TRAP, WHICH COST AN HOUR
-----------------------------------------
A .kicad_sch embeds its symbol LIBRARY as `(symbol ...)` blocks alongside the
PLACED instances, and the two are indistinguishable by their opening line. A
first version matched both and reported 49 symbols outside the page borders,
with references like `J`, `C` and `R` carrying no number and coordinates near
the origin. Those were library definitions in symbol-local coordinates.
**A placed instance carries `(lib_id ...)`; a definition does not.** The real
answer was one symbol, not 49.

Property coordinates in a .kicad_sch are ABSOLUTE page positions, unlike a
.kicad_pcb where they are relative to the footprint. Checked directly rather
than assumed: R11's symbol sits at (190.5, 69.85) and its reference text at
(196.5, 39.85).
"""
import sys, os, re, glob, math

HERE = os.path.dirname(os.path.abspath(__file__))
SCH_DIR = os.path.normpath(os.path.join(HERE, "..", "hardware", "pcb"))

# KiCad paper sizes in mm, landscape.
PAPER = {"A5": (210, 148), "A4": (297, 210), "A3": (420, 297),
         "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841)}

BORDER = 10.0          # the printed frame, all four sides
TB_W, TB_H = 110.0, 32.0   # title block, bottom right, KiCad default sheet
CHAR_W = 0.72          # width per character at 1.27 mm text, measured off a plot
BODY = 3.0             # fallback half-extent when a symbol has no graphics
NEAR = 0.6             # mm; below this a gap reads as contact on a plot


def sexp(t, i):
    """The block starting at t[i], which must be '('."""
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(":
            d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0:
                return t[i:j + 1]
    return t[i:]


def lib_extents(t):
    """Half-extents of each library symbol, from its own graphics.

    A symbol's body size is not in the placed instance, it is in the embedded
    library definition, in symbol-local coordinates. Without this the crossing
    check has to guess a body size, and a guess that fits a resistor is wrong
    for a twenty-pin connector."""
    out = {}
    lib = re.search(r"^\t\(lib_symbols\b", t, re.M)
    if not lib:
        return out
    block = sexp(t, lib.start() + 1)
    for m in re.finditer(r'\(symbol "([^"]+)"', block):
        name = m.group(1)
        if ":" not in name:          # sub-units are "Device:R_0_1", skip those
            continue
        blk = sexp(block, m.start())
        xs, ys = [], []
        for g in re.finditer(r"\((?:rectangle|polyline|circle|arc)\b", blk):
            gb = sexp(blk, g.start())
            for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", gb):
                xs.append(float(a)); ys.append(float(b))
            for a, b in re.findall(r"\((?:start|end|center|mid) ([-\d.]+) ([-\d.]+)\)", gb):
                xs.append(float(a)); ys.append(float(b))
        if xs:
            out[name] = (max(abs(min(xs)), abs(max(xs))),
                         max(abs(min(ys)), abs(max(ys))))
    return out


def lib_reach(t):
    """Half-extents INCLUDING pins, for the border check.

    Deliberately separate from lib_extents(), which is body-only and must stay
    that way: the crossing check asks "does this label sit on the part", and a
    label lying along a pin stub reads fine. The border check asks a different
    question -- "is any ink off the page" -- and a pin is ink.

    The distance between the two answers is not small. Device:C has a body
    half-height of 0.762 mm and pins reaching 3.81 mm, a factor of five. C21 on
    panel-io sat with its body inside the frame at 408.43 and its lower pin
    through it at 411.48, and the body-only check passed it."""
    out = {}
    lib = re.search(r"^\t\(lib_symbols\b", t, re.M)
    if not lib:
        return out
    block = sexp(t, lib.start() + 1)
    body = lib_extents(t)
    for m in re.finditer(r'\(symbol "([^"]+)"', block):
        name = m.group(1)
        if ":" not in name:
            continue
        blk = sexp(block, m.start())
        ex, ey = body.get(name, (0.0, 0.0))
        for p in re.finditer(r"\(pin \w+ \w+", blk):
            pb = sexp(blk, p.start())
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)", pb)
            ln = re.search(r"\(length ([\d.]+)\)", pb)
            if not at:
                continue
            px, py = float(at.group(1)), float(at.group(2))
            ang, L = float(at.group(3)), float(ln.group(1)) if ln else 0.0
            # the pin ANCHOR is the connect point; the stub runs back into
            # the body, so the tip is the far end at 180 degrees from `ang`
            tx = px - L if ang == 0 else px + L if ang == 180 else px
            ty = py - L if ang == 270 else py + L if ang == 90 else py
            ex = max(ex, abs(px), abs(tx))
            ey = max(ey, abs(py), abs(ty))
        if ex or ey:
            out[name] = (ex, ey)
    return out


def placed_symbols(t):
    """Instances only. See THE LIB_SYMBOLS TRAP above."""
    out = []
    for m in re.finditer(r"^\t\(symbol\b", t, re.M):
        blk = sexp(t, m.start() + 1)
        if "(lib_id " not in blk:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
        ref = re.search(r'\(property "Reference" "([^"]*)"', blk)
        if not at:
            continue
        lid = re.search(r'\(lib_id "([^"]+)"', blk)
        out.append({"ref": ref.group(1) if ref else "?",
                    "x": float(at.group(1)), "y": float(at.group(2)),
                    "lib": lid.group(1) if lid else "",
                    "blk": blk})
    return out


def texts(t):
    """Every visible text with a position: labels, and symbol fields."""
    out = []
    for kind in ("label", "global_label", "hierarchical_label", "text"):
        for m in re.finditer(r'\(%s "([^"]*)"' % kind, t):
            blk = sexp(t, m.start())
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
            sz = re.search(r"\(size ([\d.]+)", blk)
            if not at:
                continue
            out.append({"s": m.group(1), "x": float(at.group(1)),
                        "y": float(at.group(2)),
                        "rot": float(at.group(3) or 0),
                        "h": float(sz.group(1)) if sz else 1.27,
                        "kind": kind})
    for sym in placed_symbols(t):
        for pm in re.finditer(r'\(property "(Reference|Value)" "([^"]*)"', sym["blk"]):
            pb = sexp(sym["blk"], pm.start())
            if "(hide yes)" in pb:
                continue
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", pb)
            sz = re.search(r"\(size ([\d.]+)", pb)
            if not at:
                continue
            out.append({"s": pm.group(2), "x": float(at.group(1)),
                        "y": float(at.group(2)),
                        "rot": float(at.group(3) or 0),
                        "h": float(sz.group(1)) if sz else 1.27,
                        "kind": pm.group(1), "owner": sym["ref"]})
    return out


def box(tx, anchored=False):
    """Text bounding box. Width is ESTIMATED from character count.

    `anchored` matters and is easy to get wrong. A net LABEL is anchored at the
    end that touches the wire and grows away from it; a symbol FIELD is centred
    on its position. Treating a label as centred halves its reach and hides
    exactly the overlaps this file exists to find: BIAS_E_L anchors at
    (110.49, 138.43) and its text runs UP toward R51, which a centred box never
    sees. Directions verified against a 300 dpi plot, not assumed."""
    w = max(len(tx["s"]), 1) * CHAR_W * (tx["h"] / 1.27)
    h = tx["h"]
    if anchored:
        r = round(tx["rot"]) % 360
        x, y = tx["x"], tx["y"]
        if r == 0:      return (x, y - h / 2, x + w, y + h / 2)
        if r == 180:    return (x - w, y - h / 2, x, y + h / 2)
        if r == 90:     return (x - h / 2, y - w, x + h / 2, y)
        if r == 270:    return (x - h / 2, y - w, x + h / 2, y)
    if round(tx["rot"]) % 180 == 90:
        w, h = h, w
    return (tx["x"] - w / 2, tx["y"] - h / 2, tx["x"] + w / 2, tx["y"] + h / 2)


def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def main():
    strict = "--strict" in sys.argv
    files = sorted(glob.glob(os.path.join(SCH_DIR, "*.kicad_sch")))
    if not files:
        sys.exit(f"  no schematics under {SCH_DIR}")

    total = 0
    for f in files:
        t = open(f).read()
        name = os.path.basename(f)
        pm = re.search(r'\(paper "([^"]+)"', t)
        if not pm or pm.group(1) not in PAPER:
            print(f"  {name}: unknown paper size, skipped")
            continue
        W, H = PAPER[pm.group(1)]
        syms = placed_symbols(t)
        txs = texts(t)
        reach = lib_reach(t)
        found = []

        # 1. outside the drawing border
        #
        # Test the EXTENT, not the origin, and include power symbols. Both of
        # those cost a real miss: C21 on panel-io had its origin at y 407.67,
        # inside the 410 frame, while its lower pin reached 411.48 -- and the
        # GND flag under it sat at 416.56 with its bottom edge 0.9 mm from the
        # paper edge, never tested at all because its reference starts with #.
        # A power flag is ink on the plot like anything else.
        for s in syms:
            ex, ey = reach.get(s["lib"], (0.0, 0.0))
            lo_x, hi_x = s["x"] - ex, s["x"] + ex
            lo_y, hi_y = s["y"] - ey, s["y"] + ey
            over = []
            if lo_x < BORDER:      over.append(f"left by {BORDER - lo_x:.2f}")
            if hi_x > W - BORDER:  over.append(f"right by {hi_x - (W - BORDER):.2f}")
            if lo_y < BORDER:      over.append(f"top by {BORDER - lo_y:.2f}")
            if hi_y > H - BORDER:  over.append(f"bottom by {hi_y - (H - BORDER):.2f}")
            if over:
                name = s["ref"] if not s["ref"].startswith("#") else s["lib"].split(":")[-1]
                found.append(("border",
                              f"{name} at ({s['x']:.2f},{s['y']:.2f}) crosses the "
                              f"frame, {' and '.join(over)} mm"))

        # 2. inside the title block
        for s in syms:
            if s["ref"].startswith("#"):
                continue
            if s["x"] > W - BORDER - TB_W and s["y"] > H - BORDER - TB_H:
                found.append(("titleblock",
                              f"{s['ref']} at ({s['x']:.2f},{s['y']:.2f}) "
                              f"is inside the title block"))

        # 3. a label crossing a symbol body
        #
        # AGAINST REAL EXTENTS, BOTH SIDES. A first version compared the label
        # ANCHOR to the symbol ORIGIN and found nothing, while a 300 dpi plot
        # showed labels plainly clipping resistor bodies. Rotated text extends
        # BACK OVER the symbol from an anchor that is itself well clear: on
        # audio.kicad_sch, BIAS_E_L anchors 8.89 mm from R51 and still crosses
        # it. Anchor distance is the wrong question.
        ext = lib_extents(t)
        for tx in txs:
            if tx["kind"] not in ("label", "global_label", "hierarchical_label"):
                continue
            tb = box(tx, anchored=True)
            for s in syms:
                if s["ref"].startswith("#"):
                    continue
                ex, ey = ext.get(s["lib"], (BODY, BODY))
                sb = (s["x"] - ex, s["y"] - ey, s["x"] + ex, s["y"] + ey)
                if overlap(tb, sb):
                    found.append(("crossing",
                                  f"label {tx['s']!r} crosses {s['ref']}"))
                    break
                gx = max(tb[0], sb[0]) - min(tb[2], sb[2])
                gy = max(tb[1], sb[1]) - min(tb[3], sb[3])
                gap = max(gx, gy)
                if 0 <= gap <= NEAR:
                    found.append(("near",
                                  f"label {tx['s']!r} clears {s['ref']} by only "
                                  f"{gap:.2f} mm, reads as touching"))
                    break

        # 4. overlapping text, advisory
        boxes = [(box(x), x) for x in txs]
        seen = set()
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if overlap(boxes[i][0], boxes[j][0]):
                    a, b = boxes[i][1]["s"], boxes[j][1]["s"]
                    k = tuple(sorted((a, b)))
                    if k in seen:
                        continue
                    seen.add(k)
                    found.append(("text", f"{a!r} overlaps {b!r}"))

        print(f"\n  {name}  ({pm.group(1)}, {W}x{H} mm, {len(syms)} symbols)")
        if not found:
            print("      clean")
        for kind, msg in found:
            flag = "advisory" if kind in ("text", "near") else "   "
            print(f"      [{kind:10}] {flag} {msg}")
        total += len([x for x in found if x[0] not in ("text", "near")])

    print(f"\n  {total} finding(s) that are not advisory")
    print("  Text overlap is ADVISORY: character widths are estimated, so a"
          "\n  near-miss can read as a hit. Trust the border, title block and"
          "\n  crossing checks; eyeball the rest against the plotted PDF.")
    return 1 if (strict and total) else 0


if __name__ == "__main__":
    sys.exit(main())
