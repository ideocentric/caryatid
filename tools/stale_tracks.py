#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Find tracks left sitting on a pad whose net has moved out from under them.

    python3 tools/stale_tracks.py
    python3 tools/stale_tracks.py --check          # exit 1 on any hit
    python3 tools/stale_tracks.py --margin 0.2     # widen the search

RUN THIS AFTER EVERY "UPDATE PCB FROM SCHEMATIC" THAT SPLITS A NET.

WHAT IT CATCHES
---------------
KiCad reassigns PAD nets when you update the board from the schematic. It leaves
TRACKS alone. So every time a net is split -- inserting a jumper is exactly
that -- the tracks that used to serve the moved pads stay where they are and now
sit against a pad of a different net.

That is a short, and it is one that arrives as dead boards. It happened once
already here, on the left-channel jumpers (`0491e70`): four segments, up to
15.84 mm long, joining MIC_L to BIAS_E_L and to BYPASS_L.

DRC finds them too, as clearance and short violations. What DRC does not do is
say *which* of the two items is the residue -- it reports a pair and leaves you
to work out that the track is the leftover and the pad is innocent. This tool
answers that directly and prints endpoints you can jump to in the editor.
**DRC remains the authority.** This is a locator that runs beside it.

THE MODEL: AN ENDPOINT, NEAR A PAD, ON THE SAME LAYER, ON ANOTHER NET
----------------------------------------------------------------------
Three models were tried. The two that failed are the reason this one is written
down.

**Proximity, ignoring clearance.** The first attempt, during the left-channel
work, called any track *passing near* a pad an overlap: 32 candidates against
DRC's 4, and it looked authoritative. Twenty-eight phantoms.

**Full clearance checking.** Re-implementing DRC's rule -- segment-to-pad
distance against the netclass clearance -- reports **61 hits on a board DRC
calls clean**. The pad model here is a bounding box that ignores a pad's own
rotation inside its footprint, so around a QFN or an oval socket pad it is wrong
by of order 0.1 mm, and at a 0.25-0.30 mm rule that error IS the answer. Do not
reach for this again without fixing the pad geometry first.

**Endpoints, at the board's own minimum clearance.** Calibrated against the
known-answer case -- the board immediately before `0491e70`, where DRC found
exactly four:

    margin   before 0491e70   current board (DRC clean)
    0.001            2                0        misses both R64.1 segments
    0.10             4                0        <- exactly DRC's four
    0.15             4                0        <- and stable
    0.20             6                2        picks up legitimate routing

**0.15 mm is not a tuned number**: it is `min_clearance` in
`caryatid.kicad_pro`, the absolute floor below which no copper on this board may
approach any other. A track endpoint closer than that to a foreign pad is either
a short or was routed to that pad before its net moved.

Note what the exact-touch test alone would have missed: both R64.1 segments stop
**0.08 mm** short of the pad. Not touching. 0.08 mm away, against a 0.25 mm
rule -- a dead board, and an invisible one.

LAYERS ARE NOT OPTIONAL. An SMD pad exists on ONE copper layer; a through-hole
pad exists on every one. The layer-blind version reported two phantom shorts
under R32 -- B.Cu tracks passing beneath a front-side 0603, two layers apart.

REPORT ONLY. It writes nothing. Deleting a track is one click in the editor you
are already in to re-route, and an automatic delete on a board this far along
buys little for the risk -- the last cascade here started with a delete that
orphaned the track feeding it.
"""
import sys, os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

DEFAULT_MARGIN = 0.15      # min_clearance in caryatid.kicad_pro


def main():
    margin = DEFAULT_MARGIN
    if "--margin" in sys.argv:
        margin = float(sys.argv[sys.argv.index("--margin") + 1])
    try:
        floor = json.load(open(C.PRO))["board"]["design_settings"]["rules"]["min_clearance"]
        if margin == DEFAULT_MARGIN and floor != DEFAULT_MARGIN:
            margin = floor
            print(f"  margin taken from min_clearance in the project: {margin}")
    except Exception:
        pass

    B = C.Board(C.PCB)
    t = B.t
    nets = {int(n): nm for n, nm in
            re.findall(r'\n\t\(net (\d+) "([^"]*)"\)', t)}

    pads = []
    for p in B.parts:
        for pad in B.pads(p):
            pad["layers"] = ({"B.Cu"} if p["back"] else {"F.Cu"}) if pad["smd"] \
                else {"F.Cu", "B.Cu"}
            pad["ref"] = p["ref"]
            pads.append(pad)

    def dist(x, y, pad):
        dx = max(pad["x"] - pad["w"] / 2 - x, 0.0, x - (pad["x"] + pad["w"] / 2))
        dy = max(pad["y"] - pad["h"] / 2 - y, 0.0, y - (pad["y"] + pad["h"] / 2))
        return (dx * dx + dy * dy) ** 0.5

    hits, orphans, n_tracks = [], [], 0
    for m in re.finditer(r"\n\t\((segment|arc)\n", t):
        blk = C.sexp(t, m.start() + 1)
        s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
        e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
        n = re.search(r"\(net (\d+)\)", blk)
        ly = re.search(r'\(layer "([^"]+)"\)', blk)
        if not (s and e and n):
            continue
        n_tracks += 1
        net = nets.get(int(n.group(1)), f"<{n.group(1)}>")
        layer = ly.group(1) if ly else "?"
        x1, y1 = float(s.group(1)), float(s.group(2))
        x2, y2 = float(e.group(1)), float(e.group(2))
        if net == "":
            orphans.append((x1, y1, x2, y2, layer))
            continue
        seen = set()
        for x, y in ((x1, y1), (x2, y2)):
            for pad in pads:
                if layer not in pad["layers"] or pad["net"] == net:
                    continue
                d = dist(x, y, pad)
                if d < margin and (pad["ref"], pad["num"]) not in seen:
                    seen.add((pad["ref"], pad["num"]))
                    hits.append((net, layer, x1, y1, x2, y2, pad, d))

    print(f"  {n_tracks} tracks, {len(pads)} pads, margin {margin} mm\n")
    if not hits and not orphans:
        print("  no track endpoint sits on a pad of another net")
        return 0

    for net, layer, x1, y1, x2, y2, pad, d in sorted(hits, key=lambda h: -h[7]):
        L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        print(f"  {net:<24} {L:6.2f} mm on {layer}")
        print(f"      ({x1}, {y1}) -> ({x2}, {y2})")
        print(f"      {d:.3f} mm from {pad['ref']}.{pad['num']}, which is now "
              f"{pad['net'] or 'unconnected'}")
    for x1, y1, x2, y2, layer in orphans:
        print(f"  ORPHAN no net on {layer} ({x1}, {y1}) -> ({x2}, {y2})")
    print(f"\n  {len(hits)} stale, {len(orphans)} orphaned")
    return 1 if "--check" in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())