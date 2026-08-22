#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placement -> fully routed board, in one command. Repeat after every move.

    python3 tools/cycle.py                # F.Cu, plus B.Cu only under A1/A2
    python3 tools/cycle.py --bcu-under A1,A2,J5
    python3 tools/cycle.py --bcu-under ""  # F.Cu only, B.Cu wholly a plane
    python3 tools/cycle.py --both-layers  # let the router use B.Cu as well
    python3 tools/cycle.py --passes 60    # shorter run while iterating

THE POINT
---------
The route is not a result to preserve. It is a rendering of the placement, at
real copper widths, so the next placement decision can be made by looking at it.
Move parts, save, run this, reopen. Nothing routed survives a cycle and nothing
routed needs to.

That includes the boost hot loop. It was hand-placed and measured, and this
throws it away every run along with everything else, because keeping it while
its components move would be worse than useless. HAND-TUNE THAT LOOP ONCE, AT
THE END. Do not ship router output for the 1 MHz switching node.

B.Cu IS NOT A ROUTING LAYER BY DEFAULT
--------------------------------------
The route before this one put ~130 tracks on the back, which cut the ground
plane into 13 islands and produced three hole_clearance violations where tracks
crossed drilled holes. A route that succeeds by shredding the return path
reports a placement as fine when it is not. So B.Cu is not declared a signal
layer, everything routes on F.Cu, and the connections that fail are real
information about where the placement is wrong.

Expect more unrouted connections this way. That is the feature.

WHAT IT DOES
------------
  1  strip every segment and via -- footprints, zones, outline stay
  2  fanout.py --apply       escapes recomputed for wherever the parts now are
  3  export_dsn.py           net classes, protected copper, inset boundary,
                             and every non-plated hole fenced -- the DSN cannot
                             say "hole", so an unfenced one gets routed across
  4  freerouting             single-threaded; its multi-threaded optimiser is
                             documented broken and generates clearance errors
  5  fix_ses.py              the session is written at 10x its declared
                             resolution; without this the import lands off-board
  6  import via pcbnew       KiCad's own ImportSpecctraSES
 6b  widen_necks.py          the router necks below min_track_width on its own;
                             widen back ONLY where DRC proves it costs nothing
  7  fill zones
  8  stitch_gnd.py --apply --grid    pad vias, then a grid tying the two pours
  9  fill zones again
 10  DRC and the twelve custom checks
"""
import sys, os, re, subprocess, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

FR   = "/Applications/freerouting.app/Contents/MacOS/freerouting"
CLI  = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KPY  = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
KSP  = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages"
PCB  = os.path.abspath(C.PCB)
DSN  = os.path.join(os.path.dirname(PCB), "caryatid.dsn")
SES  = os.path.join(os.path.dirname(PCB), "caryatid.ses")


def step(n, msg):
    print(f"\n[{n}] {msg}", flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r


def strip_copper(path=None):
    """remove every routed segment, arc and via; leave footprints, zones, outline

    Collect the spans first and cut them in one pass, back to front. Editing the
    string inside the search loop -- which is how this was first written -- moves
    every offset after the cut and quietly corrupts the file."""
    path = path or PCB
    t = open(path).read()
    spans = []
    kept = 0
    for kind in ("segment", "via", "arc"):
        for m in re.finditer(rf"^\t\({kind}\b", t, re.M):
            blk = C.sexp(t, m.start() + 1)
            # LOCKED COPPER SURVIVES. The router regenerates everything it laid,
            # but it cannot regenerate hand work: fanout only escapes radially,
            # so the SW route out of U2-5 -- which goes LEFT into the channel
            # between the pad columns, per SLVSF14B Figure 10-1 -- would be
            # deleted and never come back. Lock a track and the cycle leaves it,
            # and export_dsn already emits it to Freerouting as (type protect).
            if "(locked yes)" in blk:
                kept += 1
                continue
            end = m.start() + 1 + len(blk)
            while end < len(t) and t[end] == "\n": end += 1
            spans.append((m.start(), end))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]: merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else: merged.append((s, e))
    for s, e in reversed(merged):
        t = t[:s] + t[e:]
    open(path, "w").write(t)
    strip_copper.kept = kept
    return len(spans)


def pours(t):
    out = []
    for m in re.finditer(r"^\t\(zone", t, re.M):
        z = C.sexp(t, m.start() + 1)
        nm = re.search(r'\(net_name "([^"]*)"\)', z)
        pr = re.search(r"\(priority (\d+)\)", z)
        pm = re.search(r"\(polygon", z)
        if nm and pr and pm and int(pr.group(1)) > 0:
            poly = [(float(u), float(v)) for u, v in
                    re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", C.sexp(z, pm.start()))]
            if len(poly) >= 3: out.append((nm.group(1), poly))
    return out


def inpoly(poly, q):
    x, y = q; c = False
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
    return c


def strip_pour_links():
    t = open(PCB).read()
    nets = {int(i): n for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', t)}
    pz = pours(t)
    spans = []
    for m in re.finditer(r"^\t\(segment", t, re.M):
        b = C.sexp(t, m.start() + 1)
        n = re.search(r"\(net (\d+)\)", b)
        s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
        e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
        if not (n and s and e): continue
        net = nets.get(int(n.group(1)))
        a = (float(s.group(1)), float(s.group(2)))
        c = (float(e.group(1)), float(e.group(2)))
        # both ends in ANY pour of this net -- not necessarily the SAME pour.
        # +5V_RAW and VOUT are each drawn as several separate polygons, so a link
        # between two of them failed the same-pour test and survived as real
        # copper. Two of those ran straight across a foreign pad: U2-6 to R7-1
        # is 3.27 mm with R7-2 (/power/FB) directly between them, and a 25.7 mm
        # VOUT link crossed R6-1 (/power/EN_SW). Both were reported as shorts.
        ina = any(pnet == net and inpoly(poly, a) for pnet, poly in pz)
        inc = any(pnet == net and inpoly(poly, c) for pnet, poly in pz)
        for pnet, poly in pz:
            if pnet == net and ina and inc:
                end = m.start() + 1 + len(b)
                while end < len(t) and t[end] == "\n": end += 1
                spans.append((m.start(), end)); break
    for s, e in sorted(spans, reverse=True):
        t = t[:s] + t[e:]
    open(PCB, "w").write(t)
    return len(spans)


def fill_zones():
    return run([KPY, "-c",
        f"import sys;sys.path.insert(0,'{KSP}');import wx;wx.App(False);import pcbnew;"
        f"b=pcbnew.LoadBoard('{PCB}');pcbnew.ZONE_FILLER(b).Fill(b.Zones());"
        f"pcbnew.SaveBoard('{PCB}',b)"])


def main():
    both = "--both-layers" in sys.argv
    bcu = None
    if "--bcu-under" in sys.argv:
        bcu = sys.argv[sys.argv.index("--bcu-under") + 1]
    elif not both:
        bcu = "A1,A2"        # the Seed sockets: 40 pins, one 0.25 mm channel
                             # between neighbours, 29 of 83 unrouted on one layer
    passes = "200"
    if "--passes" in sys.argv:
        passes = sys.argv[sys.argv.index("--passes") + 1]
    t0 = time.time()
    backup = PCB + ".before-cycle"
    shutil.copy(PCB, backup)
    print(f"  backup: {os.path.basename(backup)}")
    print("  routing layer(s): " + ("F.Cu + B.Cu everywhere" if both else
          f"F.Cu, plus B.Cu only under {bcu}" if bcu else "F.Cu only"))

    step(1, "stripping routed copper")
    n = strip_copper()
    print(f"    removed {n} segments/vias, kept {getattr(strip_copper,'kept',0)} locked")

    step(2, "regenerating fine-pitch escapes")
    r = run([sys.executable, os.path.join(HERE, "fanout.py"), "--apply"])
    print("   ", (r.stdout.strip().splitlines() or ["-"])[-1])

    step(3, "exporting DSN")
    cmd = [sys.executable, os.path.join(HERE, "export_dsn.py")]
    if both: cmd += ["--both-layers"]
    elif bcu: cmd += ["--bcu-under", bcu]
    r = run(cmd)
    for l in r.stdout.strip().splitlines()[1:]: print("   ", l)

    step(4, f"routing (freerouting, single-threaded, {passes} passes)")
    if os.path.exists(SES): os.remove(SES)
    r = run([FR, "-de", DSN, "-do", SES, "-mp", passes, "-mt", "1"])
    for l in (r.stdout or "").splitlines():
        if "Auto-routing stage completed" in l or "could not be routed" in l:
            print("   ", l.split("INFO")[-1].strip()[:150])
    if not os.path.exists(SES):
        print("    freerouting produced no session -- stopping"); return 1

    step(5, "correcting the session resolution")
    r = run([sys.executable, os.path.join(HERE, "fix_ses.py")])
    print("   ", (r.stdout.strip().splitlines() or ["-"])[0])

    step(6, "importing the route")
    r = run([KPY, "-c",
        f"import sys;sys.path.insert(0,'{KSP}');import wx;wx.App(False);import pcbnew;"
        f"b=pcbnew.LoadBoard('{PCB}');print('ok',pcbnew.ImportSpecctraSES(b,'{SES}'),len(b.GetTracks()));"
        f"pcbnew.SaveBoard('{PCB}',b)"])
    print("   ", [l for l in r.stdout.splitlines() if l.startswith("ok")] or r.stderr[-200:])

    step("6b", "widening necked tracks")
    # Freerouting narrows a trace on its own when it cannot otherwise fit, and
    # it does not stop at min_track_width -- the run behind `a68ae67` came back
    # with 0.1874 and 0.125 mm on ISET, TS, ILIM, FB and SW3_F, neither of which
    # appears anywhere in the .dsn going out. Below the floor is a fab reject.
    #
    # widen_necks.py repairs it ONLY when the repair is provably free: it counts
    # clearance, short, hole and dangling violations, widens, counts again, and
    # restores the original board if any of them rose. On this board they do
    # rise -- widening all eleven adds five clearance violations -- so the tool
    # reverts and says so. That is the useful answer, not a failure: the necks
    # are load-bearing and the fix is routing space, which is a placement
    # question and not something a post-process can invent.
    r = run(["python3", os.path.join(HERE, "widen_necks.py"), "--apply"])
    for line in r.stdout.splitlines():
        if line.strip() and not line.strip().startswith("0."):
            print("   ", line.strip())

    step(7, "removing pour links")
    # export_dsn emits a straight wire between the pads a pour already joins, so
    # the router does not re-route across the pour. Those are INFORMATION, not
    # copper -- but Freerouting echoes them into the session and they import as
    # real tracks. One ran 6.70 mm from U2-3 to L1-1 straight through the middle
    # of a SOT-563, shorting SW to VOUT and bridging solder mask to two more pads.
    # The pour weaves around those pins; a straight line between pad centres does
    # not. So drop any track whose net is poured and whose BOTH ends lie inside
    # that pour -- the zone is the real copper there.
    print(f"    removed {strip_pour_links()} link(s) that imported as copper")

    step(7, "filling zones")
    fill_zones()

    step(8, "stitching ground")
    r = run([sys.executable, os.path.join(HERE, "stitch_gnd.py"), "--apply", "--grid"])
    for l in r.stdout.strip().splitlines():
        if "wrote" in l or "grid stitching" in l or "unconnected" in l: print("   ", l.strip())

    step(9, "refilling zones")
    fill_zones()

    step(10, "checking")
    run([CLI, "pcb", "drc", "-o", "/tmp/cycle-drc.rpt", PCB])
    import collections
    txt = open("/tmp/cycle-drc.rpt").read() if os.path.exists("/tmp/cycle-drc.rpt") else ""
    kinds = collections.Counter(re.match(r"\[([a-z_]+)\]", l.strip()).group(1)
                                for l in txt.splitlines() if re.match(r"\[([a-z_]+)\]", l.strip()))
    lines = txt.splitlines(); items, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith("[unconnected_items]"):
            det = [l.strip() for l in lines[i+1:i+5] if l.strip().startswith("@")]
            items.append(det); i += 1 + len(det)
        else: i += 1
    real = [d for d in items if not all("Zone" in x for x in d)]
    for k, n in kinds.most_common(): print(f"    {n:5d}  {k}")
    print(f"\n    of {len(items)} unconnected entries, {len(real)} are real connections "
          f"and {len(items)-len(real)} are stranded pour islands")
    r = run([sys.executable, os.path.join(HERE, "check_board.py")])
    print("   ", (r.stdout.strip().splitlines() or ["-"])[-1])
    print(f"\n  {time.time()-t0:.0f}s.  Reload the board in KiCad (File > Revert).")
    print(f"  To undo this cycle: cp {os.path.basename(backup)} {os.path.basename(PCB)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())