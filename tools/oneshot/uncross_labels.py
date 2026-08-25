#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Push every label clear of the symbol it prints over.

    python3 tools/oneshot/uncross_labels.py            # report
    python3 tools/oneshot/uncross_labels.py --apply

WHY THIS EXISTS AND WHY IT IS THE EXCEPTION
--------------------------------------------
check_schematic.py reports and never edits, because "moving a label to clear a
symbol usually creates a new collision somewhere else". That is still true.
This tool earns the exception by REFUSING any move that is not provably clear:
every candidate is tested against every symbol body, every other text and every
wire on the sheet, and a label with no clear position is left alone and named
rather than shoved somewhere plausible.

**The distance is never guessed.** The previous attempt guessed 2.54 mm from a
model whose CHAR_W was 1.6x too small, moved five labels by less than half what
they needed, and reported them fixed. Here the distance comes from the
obstruction's own geometry under corrected metrics, rounded UP to the 1.27 grid.

TWO CLASSES, AND THEY MOVE DIFFERENT THINGS
--------------------------------------------
Both are wire-end objects, so both are fixed by sliding outward along the wire
and lengthening it. Which object slides matches how schematics are drawn:

A. LABEL OVER A COMPONENT. A vertical net label sits at the end of a 5.08 mm
   stub below a resistor and its text is 8-10 mm long, so it runs back up over
   the part it names. BIAS_E_L reaches 3.01 mm into R51.
   -> THE LABEL MOVES, further down its stub.

B. LABEL AGAINST A POWER FLAG. On a 2.54 mm connector pitch a power symbol's
   graphic is ~5 mm tall, so it spans its neighbour's row: the GND arrow on
   J13 pin 2 reaches into D12's flag on pin 3.
   -> THE POWER SYMBOL MOVES, further out along its own wire. A power flag
   standing off to one side is conventional; a signal label shoved away from
   the pin it names is not. Labels stay aligned with their pins.

A power symbol's Value and Reference are ABSOLUTE page coordinates
(conventions rule 9), so every (at ...) in the block moves together.

THREE BUGS THIS TOOL HAD, ALL WORTH KEEPING WRITTEN DOWN
---------------------------------------------------------
1. **It skipped the obstruction in its own clearance test.** The symbol being
   cleared was passed in the skip list, so the solver "solved" class A at
   1.27 mm without ever testing the resistor it was moving away from. The
   obstruction must be skipped ONLY for the wire test, where the stub
   necessarily starts at that part's pin and would always report a hit.
2. **The label lookup assumed (at ...) follows the name.** A global_label
   carries (shape input) in between, so AMP_OUT_L was never found. Match by
   name, then confirm coordinates.
3. **A slice-based self-patch produced an empty needle** and str.replace
   inserted the payload between every character, growing this file to 17 MB.
   Rewrite a file; never patch it by computed slice.

VERIFIED BY NETLIST. A label's anchor IS its connection: slide the anchor off
the wire end and the net splits silently. The wire's far end moves with it and
the component end never moves.
"""
import sys, os, re, subprocess, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb"))
ROOT = os.path.join(PCB_DIR, "caryatid.kicad_sch")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

sys.path.insert(0, os.path.join(HERE, ".."))
import check_schematic as K

GRID = 1.27
CLEAR = 0.70          # must beat NEAR (0.60), or a fix only renames the finding
MAX_SLIDE = 25.4


def near(a, b, tol=0.005):
    return abs(a - b) < tol


def netlist(tag):
    out = f"/tmp/uncross-{tag}.net"
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


def seg_hits_box(p, q, bx):
    """Does the axis-aligned segment p-q pass through box bx?"""
    x0, y0, x1, y1 = bx
    if near(p[0], q[0]):
        if not (x0 < p[0] < x1):
            return False
        lo, hi = sorted((p[1], q[1]))
        return not (hi <= y0 or lo >= y1)
    if near(p[1], q[1]):
        if not (y0 < p[1] < y1):
            return False
        lo, hi = sorted((p[0], q[0]))
        return not (hi <= x0 or lo >= x1)
    return False


def wire_would_connect(sh, own, far, newpt):
    """Would the lengthened segment far->newpt join a DIFFERENT wire?

    Schematic wires may cross freely without connecting, but two COLLINEAR
    overlapping wires are one net, and so is a wire whose end lands on another
    wire. This check exists because the first run without it slid LEG_101_L
    12.70 mm down its stub, straight into GAINLEG_L's stub on the same x, and
    merged two nets. The netlist gate caught it and reverted -- geometry should
    have refused it a step earlier.
    """
    lo, hi = sorted((far[1], newpt[1]))
    xlo, xhi = sorted((far[0], newpt[0]))
    vert = near(far[0], newpt[0])
    for w in sh.wires:
        if w is own:
            continue
        wv = near(w[0][0], w[1][0])
        if vert and wv and near(w[0][0], far[0]):
            a, b = sorted((w[0][1], w[1][1]))
            if not (b < lo - 0.005 or a > hi + 0.005):
                return True
        if (not vert) and (not wv) and near(w[0][1], far[1]):
            a, b = sorted((w[0][0], w[1][0]))
            if not (b < xlo - 0.005 or a > xhi + 0.005):
                return True
        for e in (w[0], w[1]):          # an endpoint landing on our segment
            if vert and near(e[0], far[0]) and lo - 0.005 <= e[1] <= hi + 0.005:
                return True
            if (not vert) and near(e[1], far[1]) and \
               xlo - 0.005 <= e[0] <= xhi + 0.005:
                return True
    return False


class Sheet:
    def __init__(self, path):
        self.path = path
        self.t = open(path).read()
        self.ext = K.lib_extents(self.t)
        self.syms = K.placed_symbols(self.t)
        self.txs = K.texts(self.t)
        self.wires = []
        for m in re.finditer(r"\(wire\b", self.t):
            b = K.sexp(self.t, m.start())
            p = re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", b)
            if len(p) == 2:
                self.wires.append([(float(p[0][0]), float(p[0][1])),
                                   (float(p[1][0]), float(p[1][1])), b])

    def body(self, s):
        ex, ey = self.ext.get(s["lib"], (0.0, 0.0))
        if not (ex or ey):
            return None
        return (s["x"] - ex, s["y"] - ey, s["x"] + ex, s["y"] + ey)

    def bodies(self):
        return [(self.body(s), s) for s in self.syms if self.body(s)]

    def stub(self, pt):
        hit = []
        for w in self.wires:
            for i in (0, 1):
                if near(w[i][0], pt[0]) and near(w[i][1], pt[1]):
                    hit.append((w, w[1 - i]))
        if len(hit) != 1:
            return None, None
        return hit[0]


def crossings(sh):
    out = []
    for tx in sh.txs:
        if "label" not in tx["kind"]:
            continue
        b = K.box(tx, anchored=True)
        for bb, s in sh.bodies():
            d = K.depth(b, bb)
            if d > 0:
                out.append((tx, s, d))
    return out


def sym_boxes(sh, s, dx, dy):
    """Body plus visible fields of symbol s, shifted by (dx, dy)."""
    bb = sh.body(s)
    out = [(bb[0] + dx, bb[1] + dy, bb[2] + dx, bb[3] + dy)]
    for pm in re.finditer(r'\(property "(Reference|Value)" "([^"]*)"', s["blk"]):
        pb = K.sexp(s["blk"], pm.start())
        if "(hide yes)" in pb:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
        sz = re.search(r"\(size ([\d.]+)", pb)
        out.append(K.box({"s": pm.group(2), "x": float(at.group(1)) + dx,
                          "y": float(at.group(2)) + dy, "rot": 0,
                          "h": float(sz.group(1)) if sz else 1.27,
                          "kind": "Value"}))
    return out


def field_texts(sh, s):
    """The tx dicts belonging to s, so a symbol cannot collide with itself."""
    out = []
    for pm in re.finditer(r'\(property "(Reference|Value)" "([^"]*)"', s["blk"]):
        pb = K.sexp(s["blk"], pm.start())
        if "(hide yes)" in pb:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
        for tx in sh.txs:
            if tx["kind"] in ("Reference", "Value") and \
               near(tx["x"], float(at.group(1))) and \
               near(tx["y"], float(at.group(2))):
                out.append(tx)
    return out


def clear_at(sh, boxes, skip_txs, skip_syms):
    for bx in boxes:
        g = (bx[0] - CLEAR, bx[1] - CLEAR, bx[2] + CLEAR, bx[3] + CLEAR)
        for bb, s in sh.bodies():
            if any(s is x for x in skip_syms):
                continue
            if K.depth(g, bb) > 0:
                return False
        for tx in sh.txs:
            if any(tx is x for x in skip_txs):
                continue
            if K.depth(g, K.box(tx, anchored=("label" in tx["kind"]))) > 0:
                return False
    return True


def solve(sh, mv_tx, mv_sym, anchor, far, box_skip, wire_skip, skip_txs):
    """Returns (dx, dy, distance, new_rot or None).

    Sliding is tried first and preferred: it keeps the label reading along the
    wire it names. When sliding cannot work the label is also tried ROTATED to
    horizontal, which is the only thing that helps in a narrow channel.

    Four labels need this. LEG_101_L sits on a 10.16 mm gap between R58's pin
    and GAINLEG_L's stub, and its text is 10.53 mm long: there is no distance
    along that wire at which a vertical label fits, because the text is longer
    than the channel. Turned horizontal it needs only 1.27 mm of height and
    reaches sideways into open page. A10_DIV and PGOOD_LEG are the same problem
    in its sharpest form -- a pair of same-named labels bridging a divider
    midpoint, each blocking the other's only escape route.

    Rotation does not move the anchor, so connectivity is untouched either way.
    """
    vx, vy = anchor[0] - far[0], anchor[1] - far[1]
    L = (vx * vx + vy * vy) ** 0.5
    if L < 1e-6:
        return None
    ux, uy = vx / L, vy / L

    # A turn is expressed as (angle, justify). Direction comes from JUSTIFY,
    # not the angle -- rot 0 and rot 180 draw identically and justify decides
    # which side of the anchor the text lands on. Both horizontal options are
    # written at angle 0 so only one variable changes.
    rots = [None]
    if mv_tx is not None:
        if abs(uy) > abs(ux):
            # vertical stub: turn the text horizontal, either way
            rots += [(0, "left"), (0, "right")]
        else:
            # ALREADY horizontal: the useful move is to flip which side of the
            # anchor it reads to, keeping the angle. AUDIO_OUT_R enters A1 from
            # the left and reads rightward, straight across a socket body
            # 38 mm wide. Sliding cannot help -- the text follows the anchor.
            r = int(round(mv_tx["rot"])) % 360
            rots += [(r, "right"), (r, "left")]

    for rot in rots:
        n = 0 if rot is not None else 1
        while n * GRID <= MAX_SLIDE:
            d = n * GRID
            dx, dy = ux * d, uy * d
            if mv_tx is not None:
                cand = dict(mv_tx, x=mv_tx["x"] + dx, y=mv_tx["y"] + dy)
                if rot is not None:
                    cand["rot"], cand["justify"] = rot
                boxes = [K.box(cand, anchored=True)]
            else:
                boxes = sym_boxes(sh, mv_sym, dx, dy)
            if clear_at(sh, boxes, skip_txs, box_skip):
                newpt = (anchor[0] + dx, anchor[1] + dy)
                if any(seg_hits_box(far, newpt, bb) for bb, s in sh.bodies()
                       if not any(s is x for x in wire_skip)):
                    n += 1
                    continue
                own = sh.stub(anchor)[0] if d else None
                if d and wire_would_connect(sh, own, far, newpt):
                    n += 1
                    continue
                return (dx, dy, d, rot)
            n += 1
    return None


def solve_pair(sh, a, b, skip_syms):
    """Rotate two facing labels together. Returns (rot_a, rot_b) or None.

    The last four crossings are all one shape: a pair of labels facing each
    other across a short gap, each the sole obstacle to the other's escape.
    Solved one at a time they are insoluble by construction, because the
    solver treats the partner as immovable scenery.

    Three of the pairs are the SAME NAME on both sides -- A10_DIV, PGOOD_LEG --
    which is how a divider midpoint gets named without a wire crossing it. The
    fourth, LEG_101_L against GAINLEG_L, is two different nets nose to nose on
    one x. Same geometry either way.

    Turned back to back, one reaching left and one right, they clear each other
    and the parts above them. Neither anchor moves, so no wire changes and no
    net can merge -- which is what the sliding attempt got wrong.
    """
    opts = [(0, "left"), (0, "right")]
    for ra in opts:
        for rb in opts:
            ba = K.box(dict(a, rot=ra[0], justify=ra[1]), anchored=True)
            bb = K.box(dict(b, rot=rb[0], justify=rb[1]), anchored=True)
            g = (ba[0] - CLEAR, ba[1] - CLEAR, ba[2] + CLEAR, ba[3] + CLEAR)
            if K.depth(g, bb) > 0:
                continue
            if not clear_at(sh, [ba], [a, b], skip_syms):
                continue
            if not clear_at(sh, [bb], [a, b], skip_syms):
                continue
            return ra, rb
    return None


def partner(sh, tx):
    """The nearest other label sharing this one's x, within 15 mm."""
    best, bd = None, 15.0
    for o in sh.txs:
        if o is tx or "label" not in o["kind"]:
            continue
        if not near(o["x"], tx["x"], 0.01):
            continue
        d = abs(o["y"] - tx["y"])
        if 0 < d < bd:
            best, bd = o, d
    return best


def main():
    apply_ = "--apply" in sys.argv
    plans = {}
    fixed = stuck = 0

    for path in sorted(glob.glob(os.path.join(PCB_DIR, "*.kicad_sch"))):
        sh = Sheet(path)
        cr = crossings(sh)
        if not cr:
            continue
        print(f"\n  {os.path.basename(path)}: {len(cr)} crossing(s)")

        jobs = {}
        for tx, s, d in cr:
            power = s["ref"].startswith("#")
            key = (id(s), "sym") if power else (id(tx), "lab")
            j = jobs.setdefault(key, {"tx": tx, "sym": s, "power": power,
                                      "d": 0.0, "against": []})
            j["d"] = max(j["d"], d)
            j["against"].append(tx["s"] if power else s["ref"])

        edits = []
        for j in sorted(jobs.values(), key=lambda j: -j["d"]):
            if j["power"]:
                s = j["sym"]
                anchor = (s["x"], s["y"])
                who = f"{s['lib'].split(':')[-1]} flag at ({s['x']:.2f},{s['y']:.2f})"
                mv_tx, mv_sym = None, s
                box_skip, wire_skip = [s], [s]
                skip_txs = field_texts(sh, s)
            else:
                tx = j["tx"]
                anchor = (tx["x"], tx["y"])
                who = f"label {tx['s']!r}"
                mv_tx, mv_sym = tx, None
                # The obstruction is skipped for the WIRE test only: the stub
                # necessarily starts at its pin. Skipping it for the clearance
                # test is what made this tool "solve" class A at 1.27 mm.
                box_skip, wire_skip = [], [j["sym"]]
                skip_txs = [tx]
            w, far = sh.stub(anchor)
            if w is None:
                print(f"      STUCK  {who}: no single wire at its anchor")
                stuck += 1
                continue
            got = solve(sh, mv_tx, mv_sym, anchor, far, box_skip, wire_skip,
                        skip_txs)
            if got is None and mv_tx is not None:
                p = partner(sh, mv_tx)
                pr = solve_pair(sh, mv_tx, p, box_skip) if p else None
                if pr:
                    ra, rb = pr
                    print(f"      turn {ra[1]:5} and its partner "
                          f"{p['s']!r} {rb[1]:5}   {who} (was over "
                          f"{'/'.join(sorted(set(j['against'])))})")
                    for tgt, r in ((mv_tx, ra), (p, rb)):
                        edits.append((tgt, None, None,
                                      (tgt["x"], tgt["y"]), 0.0, 0.0, r))
                        tgt["rot"], tgt["justify"] = r
                    fixed += 1
                    continue
            if got is None:
                print(f"      STUCK  {who}: nothing clear within {MAX_SLIDE} mm")
                stuck += 1
                continue
            dx, dy, d, rot = got
            how = (f"move {d:5.2f} mm" if rot is None
                   else f"turn {rot[1]:5}" + (f" +{d:.2f}" if d else "      "))
            print(f"      {how}  {who:42} (was over "
                  f"{'/'.join(sorted(set(j['against'])))})")
            edits.append((mv_tx, mv_sym, w, anchor, dx, dy, rot))
            fixed += 1
            if mv_tx is not None:
                mv_tx["x"] += dx
                mv_tx["y"] += dy
                if rot is not None:
                    mv_tx["rot"], mv_tx["justify"] = rot
            if mv_sym is not None:
                mv_sym["x"] += dx
                mv_sym["y"] += dy
                for tx in skip_txs:
                    tx["x"] += dx
                    tx["y"] += dy
            for i in (0, 1):
                if near(w[i][0], anchor[0]) and near(w[i][1], anchor[1]):
                    w[i] = (anchor[0] + dx, anchor[1] + dy)
        if edits:
            plans[path] = edits

    print(f"\n  {fixed} fixable, {stuck} stuck")
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0

    before = netlist("before")
    baks = {}
    try:
        for path, edits in plans.items():
            t = open(path).read()
            baks[path] = path + ".bak"
            shutil.copy(path, baks[path])
            for mv_tx, mv_sym, w, anchor, dx, dy, rot in edits:
                # w is None for a rotation-only edit: the anchor does not move,
                # so there is no wire to lengthen and nothing can change nets.
                if w is not None:
                    old = w[2]
                    new = old
                    for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", old):
                        if near(float(a), anchor[0]) and near(float(b), anchor[1]):
                            new = new.replace(
                                f"(xy {a} {b})",
                                f"(xy {anchor[0]+dx:g} {anchor[1]+dy:g})", 1)
                    if t.count(old) != 1:
                        sys.exit(f"  wire not unique in {os.path.basename(path)}")
                    t = t.replace(old, new, 1)

                if mv_tx is not None:
                    found = None
                    for m in re.finditer(
                            r'\((?:label|global_label|hierarchical_label) "%s"'
                            % re.escape(mv_tx["s"]), t):
                        blk = K.sexp(t, m.start())
                        am = re.search(
                            r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)", blk)
                        if am and near(float(am.group(1)), anchor[0]) and \
                           near(float(am.group(2)), anchor[1]):
                            found = (m.start(), blk, am)
                            break
                    if not found:
                        sys.exit(f"  cannot locate {mv_tx['s']!r} at {anchor}")
                    st, blk, am = found
                    tail = f" {rot[0]:g}" if rot is not None else am.group(3)
                    nb = (blk[:am.start()] +
                          f"(at {anchor[0]+dx:g} {anchor[1]+dy:g}{tail})" +
                          blk[am.end():])
                    if rot is not None:
                        # justify is what actually decides the direction, so it
                        # is written explicitly rather than left inherited from
                        # whatever the label used to be
                        if not re.search(r"\(justify [^)]*\)", nb):
                            sys.exit(f"  {mv_tx['s']!r} has no (justify) to set")
                        nb = re.sub(r"\(justify [^)]*\)",
                                    f"(justify {rot[1]})", nb, count=1)
                    t = t[:st] + nb + t[st + len(blk):]

                if mv_sym is not None:
                    blk = mv_sym["blk"]
                    if t.count(blk) != 1:
                        sys.exit(f"  symbol not unique in {os.path.basename(path)}")
                    nb = re.sub(
                        r"\(at ([-\d.]+) ([-\d.]+)((?: [-\d.]+)?)\)",
                        lambda m: (f"(at {float(m.group(1))+dx:g} "
                                   f"{float(m.group(2))+dy:g}{m.group(3)})"), blk)
                    t = t.replace(blk, nb, 1)

            if sum(1 if c == "(" else -1 if c == ")" else 0 for c in t) != 0:
                sys.exit(f"  {os.path.basename(path)} UNBALANCED -- not writing")
            open(path, "w").write(t)
    except SystemExit:
        for p, b in baks.items():
            shutil.copy(b, p)
            os.remove(b)
        raise

    after = netlist("after")
    if before != after:
        for p, b in baks.items():
            shutil.copy(b, p)
            os.remove(b)
        ch = [n for n in set(before) & set(after) if before[n] != after[n]]
        print("\n  REVERTED -- the netlist changed.")
        print(f"    appeared: {sorted(set(after)-set(before))[:4]}")
        print(f"    vanished: {sorted(set(before)-set(after))[:4]}")
        print(f"    altered:  {sorted(ch)[:4]}")
        return 1
    for b in baks.values():
        os.remove(b)
    print(f"\n  wrote {len(plans)} sheet(s)")
    print(f"  netlist identical: {len(before)} nets, same nodes on every one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
