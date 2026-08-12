#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Correct the resolution header on a Freerouting .ses so KiCad imports it in place.

    python3 tools/fix_ses.py                    # hardware/pcb/caryatid.ses in place
    python3 tools/fix_ses.py path/to/x.ses

THE BUG THIS WORKS AROUND
-------------------------
Freerouting's session writer emits coordinates at 10x the resolution its own
header declares. Both the .dsn it reads and the .dsn it writes use
`(resolution um 10)` with coordinates in units of 0.1 um -- verified by
round-tripping a board through it, where every one of 124 placements came back
byte-identical. The .ses declares the same `(resolution um 10)` and then writes
every coordinate 10x larger.

KiCad believes the header, which is the reasonable thing to do. So the import
SUCCEEDS and puts the entire route 10x off the board:

    ImportSpecctraSES -> True,  1274 tracks added
    track extent  x 533.9..1970.4   y 319.5..1166.3 mm
    board outline x  50.0.. 200.0   y  30.0.. 120.0 mm

That is why an import can look like it did nothing: it did something, a long way
from the PCB, off the edge of where anyone is looking.

Rewriting thousands of coordinates would work and would be a thousand more
chances to be wrong. Correcting the single header line to `(resolution um 100)`
makes the file self-consistent and leaves the data untouched. Verified with
KiCad's own ImportSpecctraSES: extent becomes x 53.4..197.0, y 31.9..116.6.

This is a workaround for someone else's bug, so it checks rather than assumes:
if the file already reads `um 100`, or if the scaled result would not land
inside the board outline, it refuses instead of writing.
"""
import sys, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PCB  = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.kicad_pcb")
SES  = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.ses")


def outline(path):
    t = open(path).read()
    xs, ys = [], []
    for m in re.finditer(r"\(gr_line", t):
        i = t.find('"Edge.Cuts"', m.start(), m.start() + 400)
        if i < 0: continue
        blk = t[m.start():m.start() + 400]
        for mm in re.finditer(r"\((?:start|end) ([-\d.]+) ([-\d.]+)\)", blk):
            xs.append(float(mm.group(1))); ys.append(float(mm.group(2)))
    return min(xs), min(ys), max(xs), max(ys)


def main():
    ses = sys.argv[1] if len(sys.argv) > 1 else SES
    if not os.path.exists(ses):
        print(f"  no such file: {ses}"); return 1
    t = open(ses).read()

    res = re.findall(r"\(resolution (\w+) (\d+)\)", t)
    if not res:
        print("  no resolution declaration -- refusing to guess"); return 1
    units = {r[1] for r in res}
    if units == {"100"}:
        print("  already (resolution um 100) -- nothing to do"); return 0
    if units != {"10"}:
        print(f"  unexpected resolution {res} -- refusing"); return 1

    # what the coordinates actually are, at the corrected scale
    coords = [int(m.group(2)) for m in re.finditer(r"\(place (\S+) (-?\d+) (-?\d+)", t)]
    if not coords:
        print("  no placements to sanity-check against -- refusing"); return 1
    x0, y0, x1, y1 = outline(PCB)
    lo, hi = min(coords) / 100000, max(coords) / 100000
    if not (x0 - 1 <= lo and hi <= x1 + 1):
        print(f"  scaled x {lo:.1f}..{hi:.1f} would fall outside the outline "
              f"{x0:.1f}..{x1:.1f} -- refusing"); return 1

    open(ses, "w").write(t.replace("(resolution um 10)", "(resolution um 100)"))
    print(f"  {os.path.relpath(ses)}: resolution um 10 -> um 100 ({len(res)} places)")
    print(f"  placements now span x {lo:.1f}..{hi:.1f} mm, inside the "
          f"{x0:.1f}..{x1:.1f} outline")
    return 0


if __name__ == "__main__":
    sys.exit(main())