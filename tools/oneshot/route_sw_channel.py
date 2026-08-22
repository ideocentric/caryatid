#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hand-route the SW node out of U2-5, left into the channel, and lock it.

    python3 tools/oneshot/route_sw_channel.py --apply

WHY THIS IS A TRACK AND NOT A POUR
-----------------------------------
The /power/SW pour encloses both U2-5 and L1-2 and connects only L1-2. That is
not a fill bug, it is geometry, and `fanout.py::pour_connects` already records
it: the only ways into U2-5 are the 0.150 mm gaps above and below it in the pad
column, and at the zone's 0.25 mm min_thickness the fill cannot form a neck that
narrow. So the pour bonds L1-2 and leaves U2-5 floating, 0.29 mm short.

`cycle.py::strip_copper` records the remedy: the SW route out of U2-5 goes LEFT
into the channel between the pad columns, per SLVSF14B Figure 10-1, and it is
LOCKED because fanout only escapes radially and would never regenerate it.

GEOMETRY, measured from the board rather than assumed
-----------------------------------------------------
U2 is SOT-563. Pads 1/2/3 sit at x 72.875, pads 6/5/4 at x 74.300, each
0.68 x 0.35, so:

    central channel   x 73.215 .. 73.960   =  0.745 mm wide
    channel centre    x 73.5875            <- the route runs down this
    column pad gap    0.150 mm             <- what the fill cannot squeeze

The track leaves pad 5 westward into the channel, turns south down the centre
line, and widens to the HighCurrent class width once clear of the package,
landing inside L1-2 (x 72.80..73.95, y 82.05..85.65).

THE CLEARANCE EXCEPTION, AND WHY IT IS PRINCIPLED RATHER THAN A FUDGE
----------------------------------------------------------------------
/power/SW is HighCurrent: 1.2 mm wide, 0.30 mm clearance. In a 0.745 mm channel
that rule allows 0.745 - 2(0.30) = 0.145 mm of copper -- below the board's own
0.20 mm minimum width. The two rules cannot both be satisfied here.

**The 0.30 mm clearance is unachievable inside this footprint by construction.**
U2's own pads are 0.150 mm apart. A rule demanding 0.30 mm between a SW track
and a GND pad, on a package whose SW pad is already 0.150 mm from that same GND
pad, cannot be met by any routing at all. It is a board-level creepage rule
meeting a package-level pitch, and the package wins.

So the track is drawn at the WIDTH floor, 0.20 mm, giving 0.2725 mm of
clearance on both sides -- symmetric, because the centre line is the best
available spot. That is 0.0275 mm short of the netclass rule and well above
JLC's 0.127 mm capability. The alternative, 0.145 mm copper, would meet the
clearance rule by carrying 1.5 A peak on a trace thinner than the board's
minimum, which trades a paper violation for an electrical one.

Expect DRC to report clearance against U2-2, U2-3 and U2-4 at 0.2725 mm. Those
want an exclusion with this reason recorded, not a rule change.
"""
import sys, os, re, uuid, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
import check_board as C

PCB = C.PCB
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

CHANNEL_X = 73.5875     # centre of the 0.745 mm channel between the pad columns
NECK = 0.20             # the board's minimum track width -- see the docstring
INTO_PAD_Y = 82.60      # 0.55 mm inside L1-2, whose top edge is at y 82.05

# (start, end, width) -- pad 5 west into the channel, then south into L1-2.
#
# IT DOES NOT WIDEN, AND THE FIRST VERSION OF THIS WAS WRONG TO. Widening to the
# 1.2 mm class width once "clear of the package" sounds right and does not fit:
# measured against the board, a 1.2 mm track on this centre line OVERLAPS the
# VOUT pour by 0.18 mm and both U2 pad columns by 0.23 mm. DRC caught it.
#
#     width   to VOUT pour   to U2-3    to U2-4
#      0.2      +0.3175      +0.2725    +0.2725
#      0.6      +0.1175      +0.0725    +0.0725
#      1.2      -0.1825      -0.2275    -0.2275
#
# And widening buys nothing anyway. L1-2 is 1.15 x 3.60 mm of solid copper, so
# once the track reaches the pad, the pad is the conductor. The run is 3.06 mm.
PATH = [
    ((74.300, 80.250), (CHANNEL_X, 80.250), NECK),
    ((CHANNEL_X, 80.250), (CHANNEL_X, INTO_PAD_Y), NECK),
]


def uid(*p):
    return str(uuid.uuid5(NS, "caryatid-sw-channel:" + ":".join(map(str, p))))


def main():
    t = open(PCB).read()
    nets = {n: int(i) for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
    if "/power/SW" not in nets:
        sys.exit("  no /power/SW net on this board")
    net = nets["/power/SW"]

    existing = [m for m in re.finditer(r"^\t\(segment\b", t, re.M)
                if f"(net {net})" in C.sexp(t, m.start() + 1)]
    if existing:
        sys.exit(f"  /power/SW already has {len(existing)} segment(s) -- "
                 f"this is a one-shot. Stopping.")

    out = []
    for (a, b, w) in PATH:
        out.append(f'\t(segment\n\t\t(start {a[0]} {a[1]})\n\t\t(end {b[0]} {b[1]})\n'
                   f'\t\t(width {w})\n\t\t(layer "F.Cu")\n\t\t(locked yes)\n'
                   f'\t\t(net {net})\n\t\t(uuid "{uid(a, b, w)}")\n\t)\n')
        print(f"    {a} -> {b}  {w} mm  "
              f"({math.hypot(b[0]-a[0], b[1]-a[1]):.3f} mm)  LOCKED")

    assert t.rstrip().endswith(")")
    t = t.rstrip()[:-1] + "".join(out) + ")\n"
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(PCB, "w").write(t)
    print(f"  wrote {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())