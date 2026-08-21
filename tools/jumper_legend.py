#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Silkscreen the mic capsule selector table beside JP1/JP2/JP3.

    .venv/bin/python tools/jumper_legend.py            # report a placement
    .venv/bin/python tools/jumper_legend.py --apply
    .venv/bin/python tools/jumper_legend.py --strip --apply

WHY THE LEGEND IS THE PROCEDURE, NOT A DECORATION
--------------------------------------------------
ADR 0009 accepts one real cost of jumpers over three sockets: a jumper is
mis-settable where plugging into the right hole is not. JP1 on the 5 V position
with an electret fitted puts 220R to 5 V into it.

The mitigation is that the board tells you how to decide. The capsule is
identified by measuring DC resistance across it, so the identification test is
printed *in* the table -- read the meter, read the row, set three shunts. A
legend that only named the positions would still require the datasheet.

  MIC CAPSULE
       JP1 JP2 JP3
  ELEC  12  12  12      OPEN      = ELEC
  DYN   --  12  23      150-600R  = DYN
  CARB  23  23  --      50-300R*  = CARB
                        * UNSTABLE WHEN TAPPED

"12" and "23" are pin pairs, not positions, because pin 1 is marked on the
silkscreen and "top"/"bottom" depends on which way the board is held. The
jumpers sit vertically with pin 1 uppermost, so 12 is the upper shunt.

PLACEMENT
---------
Uses pin_labels' obstacle model, so the block is checked against silk, pads,
courtyards and every label already placed. It does not force: if no clear spot
exists at any tried size, it says so and writes nothing.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C
import pin_labels as P

NS = uuid.UUID("5f9c1e2a-3b4d-4e6f-8a9b-0c1d2e3f4a5b")
THICK = 0.15
# 0.8 mm is JLC's floor for silk text height and check_board enforces it.
# There is no smaller fallback: a legend nobody can read is not a mitigation.
SIZES = (0.8,)
CLEAR = 0.26
# Line pitch, as a multiple of text size. NOT a chosen number: it is the ink
# height from pin_labels.th_split plus the 0.25 mm silk rule. A first attempt
# used 1.25 and produced nine silk_overlap violations where the lines clashed
# with EACH OTHER -- 0.08 mm actual against 0.25 required. Text that is legal
# individually still has to clear the line above it.
LINE = (sum(P.th_split(0.8)) + 0.25) / 0.8

LINES = [
    "MIC CAPSULE",
    "     JP1 JP2 JP3",
    "ELEC  12  12  12",
    "DYN   --  12  23",
    "CARB  23  23  --",
    "MEASURE DC OHMS",
    "OPEN     = ELEC",
    "150-600R = DYN",
    "50-300R  = CARB",
    "UNSTABLE = CARB",
]

# Per-position labels at each header, so the POSITION carries the answer and
# nobody has to cross-reference the table while holding a pair of tweezers.
# Above = the top pair (pins 1-2), below = the bottom pair (2-3), because the
# jumpers stand vertically with pin 1 uppermost. Three characters each: the
# headers are 4.59 mm apart, and anything longer collides with its neighbour.
POSN = {
    "JP1": ("ELE", "CAR"),    # 2k2 to 3V3A  /  220R to 5 V
    "JP2": ("AMP", "BYP"),    # op-amp       /  bypass
    "JP3": ("101", "256"),    # 1k, x101     /  392R, x256
}


def uid(s):
    return str(uuid.uuid5(NS, s))


def block_box(cx, cy, size):
    """Bounding box of the whole block centred on (cx, cy)."""
    w = max(P.tw(s, size) for s in LINES)
    h = len(LINES) * size * LINE
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), w, h


def main():
    apply_ = "--apply" in sys.argv
    strip_ = "--strip" in sys.argv
    B = C.Board(C.PCB)
    t = B.t

    # remove any previous run's block first, so this is re-runnable
    n_old = 0
    for m in reversed(list(re.finditer(r'^\t\(gr_text "', t, re.M))):
        blk = C.sexp(t, m.start() + 1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        _mine = {uid(f"line{i}") for i in range(len(LINES))} | {
            uid(f"posn{r}{s}") for r, pair in POSN.items() for s in pair}
        if u and u.group(1) in _mine:
            t = t[:m.start()] + t[m.start() + 1 + len(blk):]
            n_old += 1
    if n_old: print(f"  removed {n_old} lines from a previous run")
    if strip_:
        if apply_: open(C.PCB, "w").write(t)
        print("  stripped" + ("" if apply_ else " (dry run)"))
        return 0

    jp = {}
    for p in B.parts:
        m = re.search(r'\(property "Reference" "(JP[123])"', p["blk"])
        if m: jp[m.group(1)] = (p["x"], p["y"])
    if len(jp) != 3:
        sys.exit(f"  expected JP1-3 on the board, found {sorted(jp)}")

    obst = P.Obstacles(B)
    for box, nm in P.surviving_labels(t):
        obst.add_label(box, nm)
    x0, y0, x1, y1 = B.outline

    # try beside the jumpers first, then further out, then below
    jx = sum(v[0] for v in jp.values()) / 3
    jy = sum(v[1] for v in jp.values()) / 3
    # Search outward from the jumpers on a 1 mm grid. The block is big for a
    # silkscreen object, so a coarse handful of candidates is not enough --
    # the first attempt found nothing at 0.8 mm and silently dropped to 0.7,
    # which is under JLC's floor.
    spots = []
    for r in range(4, 46):
        for a in range(0, 360, 8):
            import math
            spots.append((jx + r * math.cos(math.radians(a)),
                          jy + r * math.sin(math.radians(a))))

    got = None
    for size in SIZES:
        for cx, cy in spots:
            box, w, h = block_box(cx, cy, size)
            if (box[0] < x0 + 1 or box[2] > x1 - 1
                    or box[1] < y0 + 1 or box[3] > y1 - 1):
                continue
            if obst.clash(box, CLEAR):
                continue
            got = (cx, cy, size, w, h)
            break
        if got: break
    if not got:
        print("  NO CLEAR SPOT for the legend at any tried size.")
        print("  Nothing written. Free space near the jumpers, or shrink LINES.")
        return 1

    cx, cy, size, w, h = got
    print(f"  block {w:.1f} x {h:.1f} mm at ({cx:.2f}, {cy:.2f}), {size} mm text")

    labels = []
    top = cy - h / 2 + size * LINE / 2
    for i, s in enumerate(LINES):
        if not s.strip(): continue
        labels.append({"label": s, "cx": cx - w / 2, "cy": top + i * size * LINE,
                       "rot": 0, "just": "left", "size": size,
                       "uuid": uid(f"line{i}")})
    t = P.emit(t, labels)
    # lock them: this block is placed once and should survive other tools
    for u in [L["uuid"] for L in labels]:
        i = t.find(f'(uuid "{u}")')
        s = t.rfind("\t(gr_text", 0, i)
        head = t.index("\n", s) + 1
        t = t[:head] + "\t\t(locked yes)\n" + t[head:]

    # --- per-position labels -------------------------------------------------
    # Placed against the same obstacle model, searching outward from the header
    # so a label never lands on the courtyard or on its neighbour.
    for box, nm in [(block_box(cx, cy, size)[0], "legend")]:
        obst.add_label(box, nm)
    posn, missed = [], []
    for ref, (top, bot) in POSN.items():
        px, py = jp[ref]
        pins_top, pins_bot = py, py + 5.08      # pin 1 and pin 3 centres
        for text, y0_, step in ((top, pins_top, -1), (bot, pins_bot, +1)):
            up, dn = P.th_split(size)
            w = P.tw(text, size)
            placed = False
            # The reference designators sit at 2.38 mm above pin 1, so a top label
            # has to clear them and land ABOVE the reference -- around 4 mm out.
            # Stopping the search at 3.5 found nothing and silently placed only
            # the bottom three.
            for gap in (1.6, 1.9, 2.2, 2.6, 3.0, 3.5, 4.0, 4.4, 4.8, 5.4, 6.0):
                ly = y0_ + step * gap
                box = (px - w/2, ly - up, px + w/2, ly + dn)
                if obst.clash(box, CLEAR): continue
                posn.append({"label": text, "cx": px, "cy": ly, "rot": 0,
                             "just": "", "size": size,
                             "uuid": uid(f"posn{ref}{text}")})
                obst.add_label(box, f"{ref}:{text}")
                placed = True
                break
            if not placed: missed.append(f"{ref} {text}")
    if missed:
        print(f"  no room for: {', '.join(missed)}")
    print(f"  {len(posn)} of 6 per-position labels placed")
    t = P.emit(t, posn)
    for u in [L["uuid"] for L in posn]:
        i = t.find(f'(uuid "{u}")')
        s2 = t.rfind("\t(gr_text", 0, i)
        h2 = t.index("\n", s2) + 1
        t = t[:h2] + "\t\t(locked yes)\n" + t[h2:]

    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"  {len(labels)} table lines + {len(posn)} position labels, "
          f"paren balance {d}")
    if d != 0:
        print("  UNBALANCED -- not writing"); return 1
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0
    open(C.PCB, "w").write(t)
    print("  written and locked")
    return 0


if __name__ == "__main__":
    sys.exit(main())