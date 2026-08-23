#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Widen tracks Freerouting necked below the board's minimum width.

    python3 tools/widen_necks.py           # report
    python3 tools/widen_necks.py --apply   # widen, verify, keep or revert

WHAT NECKS THEM, AND WHY IT IS NOT fanout.py
---------------------------------------------
Freerouting narrows a trace on its own when it cannot otherwise fit, and it does
not stop at the board's `min_track_width`. Measured on the run that produced
`a68ae67`, by comparing the widths in the file going out against the file coming
back:

    caryatid.dsn   2000 2500 5000 12000            -> 0.20 0.25 0.50 1.20 mm
    caryatid.ses   12500 18740 20000 25000 ...     -> 0.125 0.1874 0.20 0.25 ...

**12500 and 18740 appear nowhere in the input.** 12500 is exactly half of 25000
and 18740 is three quarters of it to rounding, so these are the router's own
neck-down, not anything the export asked for. fanout.py was the obvious suspect
and is innocent: its escapes all leave at 0.20 mm or wider, and the DSN proves
it.

WHY WIDENING IS NOT OBVIOUSLY SAFE
-----------------------------------
The router necked each of these BECAUSE it was tight there. Widening restores
legal copper and may create a clearance violation or a short in the same move,
which would be trading a fab reject for a dead board.

So this is all-or-nothing and verified against DRC, not asserted:

  1  count clearance/short/hole violations before
  2  widen every sub-minimum track to the floor
  3  REFILL THE ZONES -- see below
  4  count them again
  5  if ANY of those three went up, restore the original board and report

That mirrors how `0491e70` deleted its four stale tracks -- all four had to
match or nothing was written. A partial repair here would be worse than none,
because the survivors would look deliberate.

STEP 3 IS NOT OPTIONAL, AND LEAVING IT OUT CONDEMNED FOUR INNOCENT TRACKS.
A pour keeps its clearance from a track by retreating from it, so widening a
track and then asking DRC about it -- without recomputing the fill -- compares
new copper against a pour drawn for the old width. The gap it measures is a
fill artefact, not a constraint.

That is exactly what happened here. Widening all five raised `clearance` by one:

    zone clearance 0.3000 mm; actual 0.2630 mm
    Track [/power/TMR] on F.Cu  vs  Zone 'GND plane' [GND]

0.263 is 0.300 minus half the 0.075 mm the track grew -- the pour standing
still. Tested one at a time, four of the five were clean at 0.20 mm and only
TMR "failed", and it failed against a zone rather than against a pad or another
track. With ZONE_FILLER run between the widen and the check, all five pass and
DRC reports zero clearance violations.

The all-or-nothing rule then made it worse rather than safer: one false
positive reverted four real repairs. All-or-nothing is still right -- a
half-widened board reads as deliberate -- but only once the thing being
verified is the board that would actually be fabricated.

WHERE IT BELONGS. Freerouting regenerates these every run, so this is a step in
the cycle rather than a one-shot: run it after importing a session. It now
fills zones itself, so it no longer matters whether the cycle's own fill comes
before or after.
"""
import sys, os, re, json, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

PRO = os.path.join(os.path.dirname(C.PCB), "caryatid.kicad_pro")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KPY = ("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework"
       "/Versions/3.9/bin/python3")
KSP = ("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework"
       "/Versions/3.9/lib/python3.9/site-packages")
WATCH = ("clearance", "shorting_items", "hole_clearance", "track_dangling")


def floor_mm():
    return json.load(open(PRO))["board"]["design_settings"]["rules"]["min_track_width"]


def necks(t, floor):
    """(start, block, width) for every segment narrower than the floor."""
    out = []
    for m in re.finditer(r"^\t\(segment\b", t, re.M):
        blk = C.sexp(t, m.start() + 1)
        w = re.search(r"\(width ([\d.]+)\)", blk)
        if not w:
            continue
        val = float(w.group(1))
        if val < floor - 1e-9:
            net = re.search(r"\(net (\d+)\)", blk)
            st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            out.append((m.start() + 1, blk, val, net.group(1) if net else "?",
                        (st.group(1), st.group(2)) if st else ("?", "?")))
    return out


def fill_zones(path):
    """recompute every pour, so DRC judges the board that would be fabricated.

    `import wx; wx.App(False)` first -- pcbnew's Python needs a wxApp to exist
    before ZONE_FILLER touches anything, the same requirement ImportSpecctraSES
    has. It still prints a `create wxApp before calling this` assert on stderr
    and completes correctly; that line is noise, not a failure.
    """
    r = subprocess.run(
        [KPY, "-c",
         f"import sys;sys.path.insert(0,'{KSP}');import wx;wx.App(False);"
         f"import pcbnew;b=pcbnew.LoadBoard('{path}');"
         f"pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard('{path}',b)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"  zone fill failed:\n{r.stderr.strip()[:400]}")


def drc_counts(path):
    r = subprocess.run([CLI, "pcb", "drc", "--severity-all", "-o", "/dev/stdout",
                        path], capture_output=True, text=True)
    txt = r.stdout
    return {k: len(re.findall(rf"^\[{k}\]", txt, re.M)) for k in WATCH}


def main():
    apply_ = "--apply" in sys.argv
    floor = floor_mm()
    t = open(C.PCB).read()
    found = necks(t, floor)

    nets = {}
    for _, _, val, net, _ in found:
        nets.setdefault(val, []).append(net)
    print(f"  minimum track width is {floor} mm; {len(found)} track(s) below it")
    for val in sorted(nets):
        print(f"    {val} mm  x{len(nets[val])}")
    if not found:
        return 0
    for _, _, val, net, (sx, sy) in found:
        print(f"      {val:.4f} mm  net {net}  at ({sx}, {sy})")
    if not apply_:
        print("  dry run -- pass --apply to widen and verify")
        return 0

    before = drc_counts(C.PCB)
    print(f"  before: " + ", ".join(f"{k} {v}" for k, v in before.items()))

    backup = C.PCB + ".before-widen"
    shutil.copy(C.PCB, backup)
    for start, blk, val, _, _ in sorted(found, key=lambda f: -f[0]):
        new = re.sub(r"\(width [\d.]+\)", f"(width {floor})", blk, count=1)
        t = t[:start] + new + t[start + len(blk):]
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    open(C.PCB, "w").write(t)
    print(f"  widened {len(found)} track(s) to {floor} mm")
    fill_zones(C.PCB)
    print("  zones refilled")

    after = drc_counts(C.PCB)
    print(f"  after:  " + ", ".join(f"{k} {v}" for k, v in after.items()))
    worse = [k for k in WATCH if after[k] > before[k]]
    if worse:
        shutil.copy(backup, C.PCB)
        os.remove(backup)
        print(f"  REVERTED -- widening raised: "
              + ", ".join(f"{k} {before[k]}->{after[k]}" for k in worse))
        print("  those necks are LOAD-BEARING. The router narrowed them because")
        print("  the space is not there, so this cannot be fixed by widening --")
        print("  it needs routing space, which is a placement question.")
        return 1
    os.remove(backup)
    print("  kept: no clearance, short, hole or dangling violation was added")
    print("        (verified against a refilled board, not a stale pour)")
    return 0


if __name__ == "__main__":
    sys.exit(main())