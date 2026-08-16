#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mechanical tidy-up after a routing cycle. Reports first, writes with --apply.

    python3 tools/cleanup.py
    python3 tools/cleanup.py --apply

Four things, all of them consequences of how the copper got there rather than
design decisions:

  1 DUPLICATE TRACKS -- identical net, endpoints, width and layer, laid twice.
    This is locking colliding with the protected-copper round trip: strip_copper
    keeps the locked original, export_dsn hands it to Freerouting as
    (type protect), Freerouting echoes it into the session, and the import lays
    it down again. Harmless -- same net, superimposed -- but it doubles on every
    cycle, so it has to be swept.

  2 CO-LOCATED VIAS -- two drilled holes at the same coordinates, which is what
    holes_co_located reports. The stitcher can drop one onto an existing via.

  3 DANGLING VIAS -- OFF BY DEFAULT, behind --drop-dangling, because removing
    them CASCADES and eats real routing.

    A via with copper on one layer and nothing on the other looks redundant, and
    every net was indeed fully connected without the ten of them. But deleting a
    via orphans the track that fed it, that track then has a free end, deleting
    IT orphans the next one, and the deletion walks backwards along a legitimate
    route. Six dangling points became twenty-six removals and broke two real
    connections -- /audio/MIC_L at C23-1 and /panel-io/A2_W between R21-1 and
    J5-4 -- neither of which had anything to do with the vias.

    Left in place they are cosmetic. Use the flag only with a backup and check
    real-unconnected before and after.

  4 INTERSECTING SAME-NET ZONES -- KiCad requires overlapping zones to have
    distinct priorities. Drawing one net as several polygons that touch produces
    this. Bumping one priority is enough; the copper is identical either way.

WHAT IT DOES NOT DO
-------------------
It does not delete "stranded" pour islands. The zones already carry
island_removal_mode = always, so anything still present is touching something --
those are ground regions that have not reached the main plane, and they want a
stitching via, not deletion. Removing them would break connections that DRC is
currently telling you to make.

It does not touch the narrow track_width items. Those are Freerouting's own
0.1874 and 0.125 mm stubs, under the board's 0.20 mm floor. JLC would fabricate
them, so accepting them is a defensible choice -- but it is a choice, and it
belongs to whoever signs off the board, not to a cleanup script.
"""
import sys, os, re, math, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CLI = CLI if os.path.exists(CLI) else "kicad-cli"


def blocks(t, kind):
    for m in re.finditer(rf"^\t\({kind}\b", t, re.M):
        blk = C.sexp(t, m.start() + 1)
        end = m.start() + 1 + len(blk)
        while end < len(t) and t[end] == "\n": end += 1
        yield m.start(), end, blk


def drc(path):
    rpt = os.path.join(os.path.dirname(path), "cleanup-drc.rpt")
    subprocess.run([CLI, "pcb", "drc", "-o", rpt, path], capture_output=True, timeout=900)
    txt = open(rpt).read() if os.path.exists(rpt) else ""
    if os.path.exists(rpt): os.remove(rpt)
    kinds = collections.Counter(re.match(r"\[([a-z_]+)\]", l.strip()).group(1)
                                for l in txt.splitlines() if re.match(r"\[([a-z_]+)\]", l.strip()))
    lines = txt.splitlines(); items, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith("[unconnected_items]"):
            det = [l.strip() for l in lines[i+1:i+5] if l.strip().startswith("@")]
            items.append(det); i += 1 + len(det)
        else:
            i += 1
    real = [d for d in items if not all("Zone" in x for x in d)]
    return kinds, len(real), len(items) - len(real)


def prune_dangling_tracks(max_rounds=8):
    """Remove track stubs with a free end, repeatedly.

    Removing a dangling VIA orphans whatever track fed it -- taking via_dangling
    10 -> 0 took track_dangling 1 -> 6. The stubs are redundant, every net stays
    fully connected without them, but they are debris and each removal can
    expose another, so this loops until DRC stops reporting them. Locked copper
    is never touched."""
    total = 0
    for _ in range(max_rounds):
        rpt = os.path.join(os.path.dirname(C.PCB), "prune.rpt")
        subprocess.run([CLI, "pcb", "drc", "-o", rpt, C.PCB], capture_output=True, timeout=900)
        lines = open(rpt).read().splitlines() if os.path.exists(rpt) else []
        if os.path.exists(rpt): os.remove(rpt)
        pts = set()
        for i, l in enumerate(lines):
            if l.strip().startswith("[track_dangling]"):
                for j in (1, 2):
                    if i + j < len(lines):
                        m = re.match(r"@\(([\d.]+) mm, ([\d.]+) mm\)", lines[i+j].strip())
                        if m: pts.add((round(float(m.group(1)), 3), round(float(m.group(2)), 3)))
        if not pts: return total
        tt = open(C.PCB).read()
        cut = []
        for s, e, blk in blocks(tt, "segment"):
            if "(locked yes)" in blk: continue
            a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            for m2 in (a, b):
                q = (round(float(m2.group(1)), 3), round(float(m2.group(2)), 3))
                if any(math.dist(q, p) < 0.02 for p in pts):
                    cut.append((s, e)); break
        if not cut: return total
        for s, e in sorted(set(cut), reverse=True): tt = tt[:s] + tt[e:]
        open(C.PCB, "w").write(tt)
        total += len(set(cut))
    return total


def main():
    apply_ = "--apply" in sys.argv
    t = open(C.PCB).read()
    drop = []

    # 1 -- duplicate tracks
    seen, dup = {}, 0
    for s, e, blk in blocks(t, "segment"):
        a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
        b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
        w = re.search(r"\(width ([\d.]+)\)", blk)
        n = re.search(r"\(net (\d+)\)", blk)
        l = re.search(r'\(layer "([^"]+)"\)', blk)
        if not all((a, b, w, n, l)): continue
        p = tuple(sorted([(round(float(a.group(1)),4), round(float(a.group(2)),4)),
                          (round(float(b.group(1)),4), round(float(b.group(2)),4))]))
        key = (p, w.group(1), n.group(1), l.group(1))
        if key in seen:
            # keep whichever is locked
            keep_locked = "(locked yes)" in seen[key][2]
            drop.append((s, e) if keep_locked or "(locked yes)" not in blk else seen[key][:2])
            if not keep_locked and "(locked yes)" in blk: seen[key] = (s, e, blk)
            dup += 1
        else:
            seen[key] = (s, e, blk)
    print(f"  duplicate tracks         {dup}")

    # 2 and 3 -- co-located and dangling vias
    rpt_kinds, real0, isl0 = drc(C.PCB)
    dangling = set()
    rpt = os.path.join(os.path.dirname(C.PCB), "cleanup-scan.rpt")
    subprocess.run([CLI, "pcb", "drc", "-o", rpt, C.PCB], capture_output=True, timeout=900)
    lines = open(rpt).read().splitlines() if os.path.exists(rpt) else []
    if os.path.exists(rpt): os.remove(rpt)
    for i, l in enumerate(lines):
        if l.strip().startswith("[via_dangling]"):
            for j in (1, 2):
                if i+j < len(lines):
                    m = re.match(r"@\(([\d.]+) mm, ([\d.]+) mm\)", lines[i+j].strip())
                    if m: dangling.add((round(float(m.group(1)),3), round(float(m.group(2)),3)))
    pos, colo, dang = [], 0, 0
    for s, e, blk in blocks(t, "via"):
        a = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", blk)
        q = (round(float(a.group(1)),3), round(float(a.group(2)),3))
        if any(math.dist(q, p) < 0.01 for p in pos):
            drop.append((s, e)); colo += 1; continue
        pos.append(q)
        if q in dangling and "--drop-dangling" in sys.argv:
            drop.append((s, e)); dang += 1
    print(f"  co-located vias          {colo}")
    print(f"  dangling vias            {dang}"
          + ("" if "--drop-dangling" in sys.argv
             else f"   ({len(dangling)} found, left alone -- see the header)"))

    # 4 -- same-net zones that intersect
    zs = list(blocks(t, "zone"))
    bump = []
    for i in range(len(zs)):
        zi = zs[i][2]
        ni = re.search(r'\(net_name "([^"]*)"\)', zi).group(1)
        pi = int((re.search(r"\(priority (\d+)\)", zi) or type("x",(),{"group":lambda s,k:"0"})()).group(1))
        for j in range(i+1, len(zs)):
            zj = zs[j][2]
            nj = re.search(r'\(net_name "([^"]*)"\)', zj).group(1)
            pj = int((re.search(r"\(priority (\d+)\)", zj) or type("x",(),{"group":lambda s,k:"0"})()).group(1))
            if ni == nj and pi == pj and pi > 0 and (i, j) not in bump:
                bump.append((j, zs[j], pj + 1)); break
    print(f"  same-priority zone pairs {len(bump)}")

    if not apply_:
        print(f"\n  DRC now: {real0} real unconnected, {isl0} pour islands")
        print("  dry run -- pass --apply to write")
        return 0

    for idx, (s, e, blk) in [(b[0], b[1]) for b in bump]:
        pass
    # bump priorities first (indices shift after deletions, so do text edits back to front)
    edits = [(zs[j][0], zs[j][1], zs[j][2].replace(f"(priority {p-1})", f"(priority {p})", 1))
             for j, _, p in [(b[0], b[1], b[2]) for b in bump]]
    for s, e, new in sorted(edits, key=lambda x: -x[0]):
        t = t[:s] + "\t" + new + "\n" + t[e:]
    # then deletions
    for s, e in sorted(set(drop), reverse=True):
        t = t[:s] + t[e:]
    open(C.PCB, "w").write(t)
    d = sum(1 if ch == "(" else -1 if ch == ")" else 0 for ch in t)
    print(f"\n  removed {len(set(drop))} items, bumped {len(bump)} zone priorities")
    print(f"  paren balance {d}")
    return 0 if d == 0 else 1


if __name__ == "__main__":
    sys.exit(main())