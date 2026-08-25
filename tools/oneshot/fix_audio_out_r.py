#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Clear the last label crossing: AUDIO_OUT_R against A1 on seed.kicad_sch.

    python3 tools/oneshot/fix_audio_out_r.py            # report
    python3 tools/oneshot/fix_audio_out_r.py --apply

THE DEFECT
----------
AUDIO_OUT_R is 11 characters anchored at x 71.12, so its ink ends at 83.99 and
A1's body starts at 81.28. It prints 2.71 mm into the Daisy Seed socket.

Its own siblings on the same breakout show what it should be:

    AUDIO_IN_L   10 chars  anchor 68.58  ink ends 80.28  clears by 1.00
    AUDIO_IN_R   10 chars  anchor 68.58  ink ends 80.28  clears by 1.00
    AUDIO_OUT_L  11 chars  anchor 67.31  ink ends 80.18  clears by 1.10
    AUDIO_OUT_R  11 chars  anchor 71.12  ink ends 83.99  INTO A1

Same length as AUDIO_OUT_L, anchored 3.81 mm further right. Matching it fixes
the crossing exactly, and matches the drawing to itself rather than to a
preference.

WHY THIS NEEDED A THIRD EDIT, AND WHY THE AUTOMATED PASS REFUSED IT
--------------------------------------------------------------------
uncross_labels.py reported this one STUCK and was right to. The corridor at
y 120.65 that the label must slide along is occupied: a power:GND flag sits at
(68.58, 123.19) placed at **rot 180**, so its graphic is drawn ABOVE its own
wire, spanning y 120.65..123.19 at x 67.31..69.85. The label would land on it.

I first diagnosed that block as a modelling artefact -- lib_extents() builds a
box symmetric about the origin, which for power:GND (all its ink on one side of
the pin) invents 2.54 mm of empty space. That was a real defect and is now fixed
by lib_box()/placed_body(). **But fixing it did not dissolve this obstruction:
with the rotation handled correctly the ink really is at 120.65..123.19.** The
symmetric box happened to give the right answer here for the wrong reason, and
the plot confirms it -- the triangle measures 120.44..122.13 on the page.

So the GND flag turns to rot 0 and hangs below its wire at 123.19..125.73,
clear of the corridor. That is not a cosmetic preference either: of the five
power:GND symbols on this sheet the other four are at rot 0 and rot 270, and
this is the only one drawn pointing up.

Its Value text moves down 1.27 mm with it, because at rot 0 the graphic reaches
125.73 and the text box starts at 125.56 -- they would touch by 0.17 mm.
Rotating a symbol does NOT move its fields: those carry absolute page
coordinates (conventions rule 9).

THE THREE EDITS
---------------
    1  GND flag at (68.58, 123.19)   rot 180 -> 0
    2  its Value text                y 126.19 -> 127.46
    3  AUDIO_OUT_R label + its wire  x 71.12 -> 67.31

Rotating a power symbol cannot change connectivity: the pin is at the symbol
origin and the origin does not move. Edit 3 does move an anchor, so the wire's
far end moves with it and the A1 pin end never does. Netlist-gated regardless.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
SHEET = os.path.join(PCB_DIR, "seed.kicad_sch")
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

sys.path.insert(0, os.path.join(HERE, ".."))
import check_schematic as K

GND_AT = (68.58, 123.19)
VAL_FROM, VAL_TO = 126.19, 127.46
LBL_FROM, LBL_TO, LBL_Y = 71.12, 67.31, 120.65


def near(a, b, tol=0.005):
    return abs(a - b) < tol


def netlist(tag):
    out = f"/tmp/aor-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    t = open(out).read()
    return {m.group(1): sorted(re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
            for m in re.finditer(
                r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                t, re.S)}


def main():
    apply_ = "--apply" in sys.argv
    t = open(SHEET).read()
    lb = K.lib_box(t)

    gnd = [s for s in K.placed_symbols(t)
           if s["lib"] == "power:GND" and near(s["x"], GND_AT[0])
           and near(s["y"], GND_AT[1])]
    if len(gnd) != 1:
        sys.exit(f"  expected one GND at {GND_AT}, found {len(gnd)}")
    gnd = gnd[0]
    if round(gnd["rot"]) != 180:
        sys.exit(f"  that GND is at rot {gnd['rot']:.0f}, not 180 -- stopping")

    before_box = K.placed_body(gnd, lb["power:GND"])
    after_box = K.placed_body(dict(gnd, rot=0.0), lb["power:GND"])
    print(f"  GND flag at {GND_AT}")
    print(f"      rot 180 ink y {before_box[1]:.2f}..{before_box[3]:.2f}"
          f"   (in the corridor at y {LBL_Y})")
    print(f"      rot   0 ink y {after_box[1]:.2f}..{after_box[3]:.2f}   clear")

    lbl = [x for x in K.texts(t) if x["s"] == "AUDIO_OUT_R"
           and "label" in x["kind"] and near(x["x"], LBL_FROM)]
    if len(lbl) != 1:
        sys.exit(f"  expected one AUDIO_OUT_R at x {LBL_FROM}, found {len(lbl)}")
    lbl = lbl[0]
    b0 = K.box(lbl, anchored=True)
    b1 = K.box(dict(lbl, x=LBL_TO), anchored=True)
    a1 = [s for s in K.placed_symbols(t) if s["ref"] == "A1"][0]
    ab = K.placed_body(a1, lb[a1["lib"]])
    print(f"\n  AUDIO_OUT_R  ink {b0[0]:.2f}..{b0[2]:.2f}  vs A1 from {ab[0]:.2f}"
          f"   -> {b0[2]-ab[0]:+.2f} mm")
    print(f"      moved to {LBL_TO}: ink {b1[0]:.2f}..{b1[2]:.2f}"
          f"   -> clears by {ab[0]-b1[2]:.2f} mm, matching AUDIO_OUT_L")

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    bak = SHEET + ".bak"
    shutil.copy(SHEET, bak)

    # 1 + 2: the GND symbol block, angle and its Value y, in one rewrite
    blk = gnd["blk"]
    if t.count(blk) != 1:
        sys.exit("  GND block is not unique")
    nb = re.sub(r"(\(at %s %s )180(\))" % (GND_AT[0], GND_AT[1]),
                r"\g<1>0\g<2>", blk, count=1)
    if nb == blk:
        sys.exit("  could not rewrite the GND angle")
    nb2 = nb.replace(f"(at {GND_AT[0]:g} {VAL_FROM:g} 0)",
                     f"(at {GND_AT[0]:g} {VAL_TO:g} 0)", 1)
    if nb2 == nb:
        sys.exit("  could not move the GND Value text")
    t = t.replace(blk, nb2, 1)

    # 3: the label and the wire endpoint that carries it
    found = None
    for m in re.finditer(r'\((?:label|global_label|hierarchical_label) '
                         r'"AUDIO_OUT_R"', t):
        b = K.sexp(t, m.start())
        am = re.search(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", b)
        if am and near(float(am.group(1)), LBL_FROM) and \
           near(float(am.group(2)), LBL_Y):
            found = (m.start(), b, am)
            break
    if not found:
        sys.exit("  cannot locate the AUDIO_OUT_R label")
    st, b, am = found
    t = (t[:st] + b[:am.start()] +
         f"(at {LBL_TO:g} {LBL_Y:g}{am.group(3)})" +
         b[am.end():] + t[st + len(b):])

    hits = 0
    for m in list(re.finditer(r"\(wire\b", t))[::-1]:
        wb = K.sexp(t, m.start())
        pts = re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", wb)
        if len(pts) != 2:
            continue
        if not any(near(float(a), LBL_FROM) and near(float(c), LBL_Y)
                   for a, c in pts):
            continue
        nw = wb
        for a, c in pts:
            if near(float(a), LBL_FROM) and near(float(c), LBL_Y):
                nw = nw.replace(f"(xy {a} {c})", f"(xy {LBL_TO:g} {LBL_Y:g})", 1)
        t = t[:m.start()] + nw + t[m.start() + len(wb):]
        hits += 1
    if hits != 1:
        shutil.copy(bak, SHEET)
        os.remove(bak)
        sys.exit(f"  expected one wire at the label anchor, found {hits}")

    if sum(1 if c == "(" else -1 if c == ")" else 0 for c in t) != 0:
        shutil.copy(bak, SHEET)
        os.remove(bak)
        sys.exit("  UNBALANCED -- not writing")
    open(SHEET, "w").write(t)

    after = netlist("after")
    if before != after:
        shutil.copy(bak, SHEET)
        os.remove(bak)
        print("\n  REVERTED -- the netlist changed")
        return 1
    os.remove(bak)
    print(f"\n  wrote {SHEET}")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())