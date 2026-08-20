#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Restore the symbol-to-footprint link the board never had.

    .venv/bin/python tools/relink_footprints.py            # report
    .venv/bin/python tools/relink_footprints.py --apply

WHAT WAS WRONG
--------------
Every footprint on this board carried a `uuid` and no `path`. KiCad links a
schematic symbol to its footprint by the symbol's UUID path, stored on the
footprint -- so with none present, "Update PCB from Schematic" matched nothing
and offered to ADD ALL 131 COMPONENTS. Accepting that would have laid a second
copy of the entire board on top of the first.

The footprints were placed by script rather than through Update PCB from
Schematic, so the link was never written. It has been missing since placement.

WHY NOTHING CAUGHT IT
---------------------
`kicad-cli pcb drc --schematic-parity` matches by REFERENCE DESIGNATOR, not by
path, so it reported clean throughout. So did every check in check_board.py.
The defect is invisible until someone opens the board in KiCad and tries to
push a schematic change into it -- which is exactly when it does the most
damage, because the dialog looks like a normal list of additions.

WHAT THIS DOES
--------------
For every footprint whose reference matches a schematic symbol, inserts

    (path "<symbol instance path>/<symbol uuid>")
    (sheetname "<sheet>")
    (sheetfile "<sheet>.kicad_sch")

immediately before `(attr ...)`, which is where KiCad writes them.

H1-H4 and FID1-3 are deliberately skipped: they are mechanical footprints with
no schematic symbol, and giving them a path would invent a link that does not
exist. KiCad treats an unlinked footprint as board-only, which is correct.

Re-runnable. Reports what is already linked and touches only what is not.
"""
import sys, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

PCB = C.PCB
SCH_DIR = os.path.dirname(PCB)
ROOT = os.path.join(SCH_DIR, "caryatid.kicad_sch")


def sexp(t, i):
    d, j = 0, i
    while True:
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: return t[i:j + 1]
        j += 1


def sheets():
    """sheet uuid -> (name, file), from the root schematic."""
    t = open(ROOT).read()
    out = {}
    for m in re.finditer(r'\n\t\(sheet\n', t):
        blk = sexp(t, m.start() + 1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        nm = re.search(r'\(property "Sheetname" "([^"]*)"', blk)
        fl = re.search(r'\(property "Sheetfile" "([^"]*)"', blk)
        if u and fl: out[u.group(1)] = (nm.group(1) if nm else "", fl.group(1))
    return out


def symbols():
    """reference -> (full path, sheetname, sheetfile) for every schematic symbol."""
    sh = sheets()
    out = {}
    for uuid_, (name, fname) in list(sh.items()) + [(None, ("", "caryatid.kicad_sch"))]:
        p = os.path.join(SCH_DIR, fname)
        if not os.path.exists(p): continue
        t = open(p).read()
        for m in re.finditer(r'\n\t\(symbol\n', t):
            blk = sexp(t, m.start() + 1)
            su = re.search(r'\(uuid "([^"]+)"\)', blk)
            inst = re.search(r'\(path "([^"]+)"\s*\(reference "([^"]+)"', blk)
            if not (su and inst): continue
            ref = inst.group(2)
            if ref.startswith("#"): continue          # power symbols, not parts
            # THE ROOT SHEET UUID IS NOT PART OF THE FOOTPRINT PATH. A
            # symbol's `instances` path starts at the root -- "/root/audio" --
            # but the footprint carries only "/audio/<symbol uuid>". Verified
            # against KiCad's own stm32f100-discovery-shield template, a flat
            # design whose symbol instance path is "/<root>" while the matching
            # footprint path is just "/<symbol uuid>".
            #
            # Getting this wrong is silent: the file looks right, DRC parity
            # still passes because it matches on reference designator, and the
            # only symptom is Update PCB from Schematic offering to add every
            # component -- exactly the failure this tool exists to fix.
            parts = [x for x in inst.group(1).split("/") if x][1:]   # drop root
            out[ref] = ("/" + "/".join(parts + [su.group(1)]), name, fname)
    return out


def main():
    apply_ = "--apply" in sys.argv
    syms = symbols()
    t = open(PCB).read()
    linked, added, skipped, unmatched, corrected = 0, [], [], [], []

    spans = []
    for m in re.finditer(r'^\t\(footprint "', t, re.M):
        blk = sexp(t, m.start() + 1)
        r = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if r: spans.append((m.start() + 1, blk, r.group(1)))

    for start, blk, ref in sorted(spans, key=lambda q: -q[0]):
        if ref in syms and '(path "' in blk:
            want = syms[ref][0]
            cur = re.search(r'\(path "([^"]*)"\)', blk)
            if cur and cur.group(1) == want:
                linked += 1
                continue
            # wrong path -- strip the stale block so it is rebuilt below
            blk_new = re.sub(r'\n\t\t\(path "[^"]*"\)'
                             r'(\n\t\t\(sheetname "[^"]*"\))?'
                             r'(\n\t\t\(sheetfile "[^"]*"\))?', "", blk, count=1)
            t = t[:start] + blk_new + t[start + len(blk):]
            blk = blk_new
            corrected.append(ref)
        elif '(path "' in blk:
            linked += 1
            continue
        if ref not in syms:
            skipped.append(ref)                       # mechanical, no symbol
            continue
        path, sname, sfile = syms[ref]
        am = re.search(r'\n\t\t\(attr ', blk)
        if not am:
            unmatched.append(ref)
            continue
        ins = (f'\n\t\t(path "{path}")'
               f'\n\t\t(sheetname "{sname}")'
               f'\n\t\t(sheetfile "{sfile}")')
        new = blk[:am.start()] + ins + blk[am.start():]
        t = t[:start] + new + t[start + len(blk):]
        added.append(ref)

    print(f"  {len(spans)} footprints: {linked} already correct, "
          f"{len(added)} relinked, {len(corrected)} had a WRONG path corrected, "
          f"{len(skipped)} skipped (no symbol)")
    if skipped: print(f"    skipped: {' '.join(sorted(skipped))}")
    if unmatched:
        print(f"\n  ERROR: no (attr ...) to anchor against: {' '.join(unmatched)}")
        return 1
    missing = sorted(set(syms) - {r for _, _, r in spans})
    if missing:
        print(f"\n  in the schematic but NOT on the board ({len(missing)}): "
              f"{' '.join(missing)}")
        print(f"  those are the genuine additions Update PCB from Schematic "
              f"should offer.")
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"\n  paren balance {d}")
    if d != 0:
        print("  UNBALANCED -- not writing"); return 1
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0
    open(PCB, "w").write(t)
    print(f"  wrote {os.path.relpath(PCB)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())