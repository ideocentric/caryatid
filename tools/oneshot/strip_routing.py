#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Strip every track, via and zone fill, keeping placement and everything else.

    KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
    $KPY tools/oneshot/strip_routing.py            # report, write a copy
    $KPY tools/oneshot/strip_routing.py --apply

MUST RUN UNDER KiCad's BUNDLED PYTHON -- it needs `pcbnew`.

WHY
---
The routed board had no room where it needed it. ADR 0010's right-channel
jumpers could not be placed within 41.6 mm of the circuitry they select,
measured against every courtyard, pad, via and track -- while the upper board
sat largely empty. Patching around that means long analogue runs to reach a trio
of jumpers parked across the board.

So the copper goes and the placement stays. Same schematic, same footprints,
same symbol links, same BOM; the route is drawn again with the components
rebalanced into the space that is actually free.

WHAT IS REMOVED

    949 tracks   4324 mm of copper
    203 vias
     10 zone FILLS

WHAT SURVIVES, AND THIS IS THE POINT

    135 footprints, at their current positions and orientations
        every `path` linking a footprint to its schematic symbol -- these are
        the uuids, and losing one silently orphans a part from the netlist
        every net assignment on every pad
        every reference and value, so the BOM is untouched
     10 zone OUTLINES, unfilled
        silkscreen, fabrication layers, Edge.Cuts, mounting holes, fiducials

THE ZONE OUTLINES ARE KEPT BUT EIGHT OF THEM WILL GO STALE. Only two zones are
ground fill (GND on F.Cu and B.Cu). The other eight are hand-drawn power pours
-- VBAT, VOUT x3, +5V_RAW x2, VIN_DC, /power/SW -- which ADR 0008 uses AS
ROUTING rather than as plane. They are shaped around where U1 and U2 sit today,
so the moment those parts move the outlines are wrong. They are kept because
deleting them is one click and redrawing them is not, not because they remain
correct.

VERIFY AFTER RUNNING. The things that must NOT change are the point of the
exercise, so they are asserted here rather than eyeballed: footprint count,
every footprint's position, orientation and path, and every pad's net. The
script refuses to write if any of them moved.

Expect DRC to report the full ratsnest afterwards -- that is what unrouted
means. Schematic parity must stay 0: routing is not part of parity, so if it
moves, something structural was damaged.
"""
import sys, os

try:
    import pcbnew
except ImportError:
    sys.exit("  needs KiCad's bundled python -- see the docstring for the path")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
PCB = os.path.join(ROOT, "hardware", "pcb", "caryatid.kicad_pcb")


def fingerprint(board):
    """Everything that must survive, in a form that can be compared."""
    fp = {}
    for f in board.GetFootprints():
        pads = {p.GetPadName(): p.GetNetname() for p in f.Pads()}
        fp[f.GetReference()] = (
            f.GetPosition().x, f.GetPosition().y,
            round(f.GetOrientationDegrees(), 4),
            f.GetPath().AsString(),
            f.GetValue(),
            f.IsDNP(),
            tuple(sorted(pads.items())),
        )
    return fp


def main():
    apply_ = "--apply" in sys.argv
    out = PCB if apply_ else os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "caryatid-stripped.kicad_pcb")

    b = pcbnew.LoadBoard(PCB)
    before = fingerprint(b)

    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    copper = sum(pcbnew.ToMM(t.GetLength()) for t in tracks)
    print(f"  before: {len(before)} footprints, {len(tracks)} tracks "
          f"({copper:.0f} mm), {len(vias)} vias, {len(b.Zones())} zones")

    for t in list(b.GetTracks()):
        b.RemoveNative(t)
    print(f"  removed {len(tracks)} tracks and {len(vias)} vias")

    n = 0
    for z in b.Zones():
        if z.IsFilled():
            z.UnFill()
            n += 1
    print(f"  unfilled {n} zones, keeping {len(b.Zones())} outlines")

    # --- what must not have changed ----------------------------------------
    after = fingerprint(b)
    if set(before) != set(after):
        lost, gained = set(before) - set(after), set(after) - set(before)
        sys.exit(f"  FOOTPRINTS CHANGED -- lost {sorted(lost)}, "
                 f"gained {sorted(gained)}. Not writing.")
    moved = [r for r in before if before[r] != after[r]]
    if moved:
        for r in moved[:10]:
            print(f"    {r}\n      was {before[r]}\n      now {after[r]}")
        sys.exit(f"  {len(moved)} FOOTPRINTS ALTERED. Not writing.")
    print(f"  verified: {len(after)} footprints unchanged -- position, "
          f"orientation, path, value, dnp and every pad net")

    left = [t for t in b.GetTracks()]
    filled = [z for z in b.Zones() if z.IsFilled()]
    if left or filled:
        sys.exit(f"  STILL {len(left)} tracks/vias and {len(filled)} filled "
                 f"zones. Not writing.")

    b.Save(out)
    print(f"  wrote {out}")
    if not apply_:
        print("  dry run -- pass --apply to write the real board")
    return 0


if __name__ == "__main__":
    sys.exit(main())