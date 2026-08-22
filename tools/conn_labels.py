#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Silkscreen what each connector IS, beside every connector.

    python3 tools/conn_labels.py              # report placement, write nothing
    python3 tools/conn_labels.py --apply
    python3 tools/conn_labels.py --strip --apply

WHY, WHEN pin_labels ALREADY PRINTS EVERY PIN
----------------------------------------------
pin_labels answers "what is this pin". It cannot answer "what plugs in here".
J9's pins read `3V3A A5 GND`, which is true and tells you nothing: the loom is
built months after the board, by hand, and the person holding it needs to know
that connector takes the SOFT POT. connectors.md makes exactly this argument for
the pin labels; it applies one level up.

THE DESCRIPTIONS ALREADY EXIST AND DO NOT PRINT. Every connector carries its
role as its Value field -- 'Soft pot', 'Analogue bus', 'Digital bus' -- but on
**F.Fab**, which is a documentation layer and is not fabricated. So the board
knows what it is and never says so.

WHY NOT JUST MOVE THE Value FIELD TO F.SilkS
---------------------------------------------
Measured first: at 0.8 mm, seven of eighteen Value strings do not fit anywhere
near their connector. 'Comms A - module' is 14.23 mm, 'Audio in L/R/rtn' is
13.97, and the board is already carrying 77 pin labels, 109 references, the
capsule legend and the ensō.

A Value is a BOM and fab description. A silkscreen label is read by someone
holding a crimp tool. They are not the same string, so this keeps its own table
and 17 of 18 then fit. The exception is recorded below rather than forced.

SIZE is 0.8 mm, JLC's floor and the same as the capsule legend, because there is
no room for anything larger. Labels are LOCKED, like pin_labels' output, so a
re-run of another tool cannot silently revert a hand nudge.

TEXT IS EMITTED CENTRED, WITH NO `justify`, AND THAT IS LOAD-BEARING.
th_split() splits a line's height ABOUT ITS CENTRE, so the collision box this
tool tests is centred on the anchor. Emitting `(justify bottom)` -- copied from
the capsule legend, where it is correct -- anchors the BOTTOM instead, drawing
every label about half a line higher than the box that was checked. The first
run did exactly that: the model reported J3 a comfortable 0.73 mm clear of
'CHG LEDS' while DRC reported them overlapping, six times. The box and the
emitter have to agree about the anchor.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C
import pin_labels as P

NS = uuid.UUID("9d4e2b71-6c3a-4f58-9e21-7b0d5a3c8e14")
SIZE = 0.8
THICK = 0.15
CLEAR = 0.26
GAPS = (0.35, 0.6, 0.9, 1.3, 1.8, 2.4, 3.0)

# What the connector IS, not what its pins are called. Kept short because the
# board is dense; the long form lives in connectors.md and in the Value field.
#
# J6/J7/J8 and J12 look redundant against their own pin labels -- the pins
# already read SW1/SW2/SW3 and RED/GRN/BLU. They are labelled anyway so that
# EVERY connector carries one: a board where most jacks are named and three are
# not reads as an oversight, and the cost is 2.7 mm of ink each.
LABELS = {
    "J1":  "DC IN",        "J3":  "LATCH",      "J4":  "CHG LEDS",
    "J5":  "ANALOG BUS",   "J6":  "SW1",        "J7":  "SW2",
    "J8":  "SW3",          "J9":  "SOFT POT",   "J10": "FSR",
    "J11": "DIGITAL BUS",  "J12": "RGB",        "J13": "QWIIC",
    "J14": "MIC RTN",      "J15": "COMMS B",    "J16": "SPI1",
    "J17": "AUDIO OUT",    "J18": "AUDIO IN",   "J19": "COMMS A",
}


def uid(ref):
    return str(uuid.uuid5(NS, f"caryatid-connlabel-{ref}"))


def strip(t):
    """remove this tool's own labels, locked or not -- it owns them by uuid"""
    known = {uid(r) for r in LABELS}
    n = 0
    while True:
        hit = None
        for m in re.finditer(r"^\t\(gr_text\b", t, re.M):
            blk = C.sexp(t, m.start() + 1)
            u = re.search(r'\(uuid "([^"]+)"\)', blk)
            if u and u.group(1) in known:
                e = m.start() + 1 + len(blk)
                while e < len(t) and t[e] == "\n":
                    e += 1
                hit = (m.start(), e)
                break
        if not hit:
            return t, n
        t = t[:hit[0]] + t[hit[1]:]
        n += 1


def main():
    apply_ = "--apply" in sys.argv
    B = C.Board(C.PCB)
    t = B.t

    t, removed = strip(t)
    if removed:
        print(f"  removed {removed} label(s) from a previous run")
    if "--strip" in sys.argv:
        if apply_:
            open(C.PCB, "w").write(t)
            print("  stripped")
        else:
            print("  dry run -- pass --apply to write")
        return 0

    B2 = C.Board(C.PCB)
    B2.t = t
    obst = P.Obstacles(B2)
    for box, nm in P.surviving_labels(t):
        obst.add_label(box, nm)
    x0, y0, x1, y1 = B.outline

    conns = []
    for p in B.parts:
        m = re.search(r'\(property "Reference" "(J\d+)"', p["blk"])
        if m and m.group(1) in LABELS:
            conns.append((m.group(1), p))
    conns.sort(key=lambda q: int(q[0][1:]))

    placed, failed = [], []
    for ref, p in conns:
        lab = LABELS[ref]
        cy = B.courtyard(p) or (p["x"]-1, p["y"]-1, p["x"]+1, p["y"]+1)
        w = P.tw(lab, SIZE)
        up, dn = P.th_split(SIZE)
        got = None
        for gap in GAPS:
            for cx, cyy in ((p["x"], cy[1] - gap - up),      # above
                            (p["x"], cy[3] + gap + dn),      # below
                            (cy[0] - gap - w/2, p["y"]),     # left
                            (cy[2] + gap + w/2, p["y"])):    # right
                box = (cx - w/2, cyy - up, cx + w/2, cyy + dn)
                if (box[0] < x0 + 0.5 or box[2] > x1 - 0.5
                        or box[1] < y0 + 0.5 or box[3] > y1 - 0.5):
                    continue
                if obst.clash(box, CLEAR):
                    continue
                got = (cx, cyy, box)
                break
            if got:
                break
        if got:
            obst.add_label(got[2], f"conn {ref}")
            placed.append((ref, lab, got[0], got[1]))
        else:
            failed.append((ref, lab))

    for ref, lab, cx, cy in placed:
        print(f"    {ref:4} {lab:12} -> ({cx:7.2f}, {cy:6.2f})")
    for ref, lab in failed:
        print(f"    {ref:4} {lab:12} -- NO ROOM, left unlabelled")
    print(f"\n  {len(placed)} placed, {len(failed)} without room")

    out = []
    for ref, lab, cx, cy in placed:
        out.append(f'\t(gr_text "{lab}"\n\t\t(at {cx:.4f} {cy:.4f} 0)\n'
                   f'\t\t(layer "F.SilkS")\n\t\t(locked yes)\n'
                   f'\t\t(uuid "{uid(ref)}")\n\t\t(effects\n\t\t\t(font\n'
                   f'\t\t\t\t(size {SIZE} {SIZE})\n\t\t\t\t(thickness {THICK})\n'
                   f'\t\t\t)\n\t\t)\n\t)\n')
    i = t.rfind("\n)")
    t = t[:i] + "\n" + "".join(out).rstrip("\n") + t[i:]
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0
    open(C.PCB, "w").write(t)
    print(f"  wrote {len(placed)} connector labels")
    return 0


if __name__ == "__main__":
    sys.exit(main())