#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stop power-symbol text printing on top of other text.

    python3 tools/oneshot/fix_power_text.py            # report
    python3 tools/oneshot/fix_power_text.py --apply

Two defects, one cause: a power symbol's Value is drawn at a fixed offset from
its own symbol, and nothing checks where that lands.

1. POWER.KICAD_SCH -- FOUR PWR_FLAGS, VALUES HIDDEN
---------------------------------------------------
    PWR_FLAG at (69.85, 275.59), Value at (69.85, 272.59)
    VIN_DC   at (69.85, 275.59), Value at (69.85, 272.59)

Not near each other. THE SAME POINT, to the hundredth of a millimetre, on all
four rails (GND, VIN_DC, VBAT, +5V). Rendered at 600 dpi the pair prints as
"PWRN_FLDCAG": two words in the same place, neither readable.

The Value is hidden rather than moved, because on a PWR_FLAG it carries no
information. PWR_FLAG is an ERC annotation asserting that a net is driven; its
Value is the literal string "PWR_FLAG" on every instance, and the symbol's own
graphic already says what it is. The net name beneath it is the thing worth
reading, and hiding one of the two is what makes it readable.

Its Reference is already hidden in exactly this way, so this is the convention
the file already uses, not a new one.

2. PANEL-IO.KICAD_SCH -- TEN VALUES MOVED OFF THE NEXT PIN ROW
---------------------------------------------------------------
Ten labels each sit 0.46 mm from a power rail's Value text. One shape, ten
times, and the mechanism is arithmetic:

    power symbol at row Y, its Value drawn at Y + 3.00
    connector pins on a 2.54 mm pitch, so the next row is at Y + 2.54
    3.00 - 2.54 = 0.46 mm

The Value lands on the NEXT PIN DOWN, every time, wherever this pattern is
used. J13 is the clearest: pins are GND / +3V3 / D12 / D11 top to bottom, and
+3V3's name prints through D12's label.

**Moving the text UP does not work and the arithmetic says so before you try:**
the row above is another pin 2.54 mm away, so a symmetric -3.00 offset lands on
that one instead. On a 2.54 mm pitch there is no vertical room at all. The text
has to leave the column, so it moves SIDEWAYS onto its own row, clear of both
its symbol's graphic and the label flags stacked in the column.

The offset is not hardcoded. Each candidate is tested against every other text
box and every symbol body on the sheet, and the first clear one wins, so a fix
cannot silently create the collision it was meant to remove. Candidates are
tried left first because the wire runs right toward the connector.

**Positions are updated as it goes.** Ten texts moving on one sheet change the
landscape for each other; testing all ten against the ORIGINAL layout would be
the same class of error as verifying copper against a stale zone fill
(conventions rule 1).

NEITHER EDIT CAN CHANGE CONNECTIVITY -- both are field text, which carries none.
The netlist is compared anyway, because "cannot" and "did not" are different
claims.
"""
import sys, os, re, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

sys.path.insert(0, os.path.join(HERE, ".."))
import check_schematic as K

# tried in order; left first, the wire runs right toward the connector
CANDIDATES = [(-3.81, 0.0), (-5.08, 0.0), (-6.35, 0.0), (-7.62, 0.0),
              (3.81, 0.0), (5.08, 0.0), (6.35, 0.0),
              (-3.81, -1.27), (-3.81, 1.27)]
CLEAR = 0.30       # mm of daylight required, not merely "not overlapping"


def netlist(tag):
    out = f"/tmp/pwrtext-{tag}.net"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, ROOT],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"  netlist export failed: {r.stderr[:200]}")
    t = open(out).read()
    return {m.group(1): sorted(re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
            for m in re.finditer(
                r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\Z)',
                t, re.S)}


def grow(b, m):
    return (b[0] - m, b[1] - m, b[2] + m, b[3] + m)


def hide_pwr_flags(t):
    """Add (hide yes) to every PWR_FLAG Value. Returns (text, [what])."""
    done = []
    for s in K.placed_symbols(t):
        if "PWR_FLAG" not in s["lib"]:
            continue
        vm = re.search(r'\(property "Value" "', s["blk"])
        vb = K.sexp(s["blk"], vm.start())
        if "(hide yes)" in vb:
            continue
        # close of (font ...) then close of (effects ...); insert between
        em = re.search(r"\(effects\s*\n(\s*)\(font", vb)
        if not em:
            sys.exit(f"  PWR_FLAG at ({s['x']}, {s['y']}) has no (effects (font -- "
                     f"stopping rather than guessing the shape")
        ind = em.group(1)
        fb = K.sexp(vb, em.end() - len("(font"))
        cut = vb.index(fb) + len(fb)
        nvb = vb[:cut] + "\n" + ind + "(hide yes)" + vb[cut:]
        nblk = s["blk"][:vm.start()] + nvb + s["blk"][vm.start() + len(vb):]
        if t.count(s["blk"]) != 1:
            sys.exit(f"  PWR_FLAG block at ({s['x']}, {s['y']}) is not unique")
        t = t.replace(s["blk"], nblk, 1)
        done.append(f"PWR_FLAG at ({s['x']:.2f}, {s['y']:.2f})")
    return t, done


def fix_sheet_text(t):
    """Move colliding power-symbol Values sideways. Returns (text, [what])."""
    txs = K.texts(t)
    ext = K.lib_extents(t)
    syms = K.placed_symbols(t)
    bodies = []
    for s in syms:
        ex, ey = ext.get(s["lib"], (0.0, 0.0))
        if ex or ey:
            bodies.append((s["x"] - ex, s["y"] - ey, s["x"] + ex, s["y"] + ey))

    # which Values collide, and which symbol owns each
    owner = {}
    for s in syms:
        vm = re.search(r'\(property "Value" "([^"]*)"', s["blk"])
        if not vm:
            continue
        vb = K.sexp(s["blk"], vm.start())
        if "(hide yes)" in vb:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", vb)
        owner[(round(float(at.group(1)), 2), round(float(at.group(2)), 2),
               vm.group(1))] = s

    live = [dict(x) for x in txs]          # mutated as fixes land
    done = []
    for idx, a in enumerate(live):
        if a["kind"] != "Value":
            continue
        key = (round(a["x"], 2), round(a["y"], 2), a["s"])
        s = owner.get(key)
        # Identify a power symbol by its #PWR REFERENCE, not by a "power:"
        # lib prefix. The prefix test silently skipped three of these: +3V3A
        # is caryatid:+3V3A, a project-local symbol, and just as much a power
        # flag as the stock ones. Exactly the failure conventions.md warns
        # about -- a guard that is right for the files it was written against
        # and wrong one directory over.
        if s is None or not s["ref"].startswith("#PWR"):
            continue
        hit = [b for j, b in enumerate(live)
               if j != idx and K.depth(K.box(a), K.box(b)) >= K.DEEP]
        if not hit:
            continue

        chosen = None
        for dx, dy in CANDIDATES:
            cand = dict(a, x=s["x"] + dx, y=s["y"] + dy)
            cb = K.box(cand)
            if any(K.depth(grow(cb, CLEAR), K.box(b)) > 0
                   for j, b in enumerate(live) if j != idx):
                continue
            if any(K.depth(grow(cb, CLEAR), bb) > 0 for bb in bodies):
                continue
            chosen = (dx, dy, cand)
            break
        if chosen is None:
            sys.exit(f"  no clear position for '{a['s']}' at "
                     f"({a['x']:.2f}, {a['y']:.2f}) -- stopping rather than "
                     f"trading one collision for another")
        dx, dy, cand = chosen
        vm = re.search(r'\(property "Value" "', s["blk"])
        vb = K.sexp(s["blk"], vm.start())
        am = re.search(r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", vb)
        nvb = (vb[:am.start()] +
               f"(at {cand['x']:g} {cand['y']:g}{am.group(3)})" + vb[am.end():])
        nblk = s["blk"][:vm.start()] + nvb + s["blk"][vm.start() + len(vb):]
        if t.count(s["blk"]) != 1:
            sys.exit(f"  symbol block for '{a['s']}' is not unique")
        t = t.replace(s["blk"], nblk, 1)
        s["blk"] = nblk
        live[idx] = cand
        done.append(f"{a['s']:7} ({a['x']:.2f},{a['y']:.2f}) -> "
                    f"({cand['x']:.2f},{cand['y']:.2f})  offset ({dx:+.2f},{dy:+.2f})"
                    f"  was over '{hit[0]['s']}'")
    return t, done


def main():
    apply_ = "--apply" in sys.argv
    plan = {}

    p = os.path.join(PCB_DIR, "power.kicad_sch")
    t = open(p).read()
    t, hid = hide_pwr_flags(t)
    print(f"  power.kicad_sch: hide {len(hid)} PWR_FLAG Value(s)")
    for w in hid:
        print(f"      {w}")
    t2, moved = fix_sheet_text(t)
    if moved:
        print(f"  power.kicad_sch: and move {len(moved)} more")
        for w in moved:
            print(f"      {w}")
    plan[p] = t2

    # every other sheet, not just panel-io: the defect is a property of the
    # symbol's default field offset, so it appears wherever the pattern is
    # used. Idempotent -- only texts that actually collide are touched.
    for name in ("panel-io.kicad_sch", "seed.kicad_sch", "audio.kicad_sch",
                 "caryatid.kicad_sch"):
        p = os.path.join(PCB_DIR, name)
        t = open(p).read()
        t, moved = fix_sheet_text(t)
        print(f"\n  {name}: move {len(moved)} power Value(s)")
        for w in moved:
            print(f"      {w}")
        if moved:
            plan[p] = t

    if not apply_:
        print("\n  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    baks = {}
    for p, new in plan.items():
        baks[p] = p + ".bak"
        shutil.copy(p, baks[p])
        d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in new)
        if d != 0:
            sys.exit(f"  {os.path.basename(p)} UNBALANCED ({d}) -- not writing")
        open(p, "w").write(new)

    after = netlist("after")
    if before != after:
        for p, b in baks.items():
            shutil.copy(b, p)
        for b in baks.values():
            os.remove(b)
        print("\n  REVERTED -- the netlist changed, which field text cannot do")
        return 1
    for b in baks.values():
        os.remove(b)
    print(f"\n  wrote {len(plan)} sheet(s)")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())