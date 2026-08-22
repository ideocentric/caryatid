#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export hardware/pcb/caryatid.kicad_pcb as Specctra DSN, for Freerouting.

    python3 tools/export_dsn.py                 # -> hardware/pcb/caryatid.dsn
    python3 tools/export_dsn.py --with-gnd      # route GND too (see below)
    python3 tools/export_dsn.py -o /tmp/x.dsn

Then: freerouting -de caryatid.dsn -do caryatid.ses
      KiCad: File > Import > Specctra Session

KiCad can export DSN from the GUI and that route is more authoritative than this
file. This exists so the export can be produced headlessly -- `kicad-cli pcb
export` has no dsn subcommand.

WHAT THIS DOES THAT THE GUI EXPORT DOES NOT
-------------------------------------------
* **GND is excluded by default.** B.Cu is a ground plane, so GND wants stitching
  vias, not 72 routed traces. Freerouting cannot see the zone and would scribble
  ground all over the board. Pass --with-gnd if you want it routed anyway.
* **Existing copper is emitted as protected wiring.** The boost hot loop and the
  SW node were placed and measured by hand; `(type protect)` stops Freerouting
  ripping them up.
* **All four net classes are emitted, not just Default.** This file originally
  wrote one class, so Freerouting returned VBAT, VOUT, VIN_DC and SW at 0.25 mm
  -- about 0.86 A at a 10 C rise on 1 oz, against a 1.51 A boost peak. That is
  not a fab-rule violation, it is an electrical one, and DRC would not have
  caught it because 0.25 mm is legal copper.
* **The boundary is inset by EDGE_COPPER_MM** so Freerouting cannot route to the
  board edge. JLC wants 0.20 mm copper-to-edge and the outline tolerance is
  +/-0.2 mm, so the inset is 0.30.

WHAT FREEROUTING STILL DOES NOT CHECK
-------------------------------------
The DSN can only carry clearance, track width, via padstacks and the boundary.
**Annular ring, minimum drill, hole-to-hole, silkscreen and component height are
not expressible in it at all** -- Freerouting will happily return a board that
violates every one of them, because it was never told. Those are enforced before
export (via padstacks come from the netclasses) and after import, by
`tools/check_board.py` and KiCad's own DRC. A clean Freerouting run is not
evidence of a fabricable board.

CONVENTIONS, which are where this format goes wrong
---------------------------------------------------
* resolution is `um 10`, so a coordinate is millimetres x 10000
* **DSN is Y-up, KiCad is Y-down**: dsn_y = -kicad_y
* images are the CANONICAL library footprint -- unrotated, unmirrored. Rotation
  and side live in `(place ...)`. This matters here because the board stores
  back-side footprints already Y-negated; using the placed copy would mirror
  them twice.

NOT VERIFIED AGAINST FREEROUTING. There is no Freerouting on this machine, so
this has been checked structurally (balanced, complete, coordinates in range) but
never loaded by the tool it targets. Treat the first import as the real test.
"""
import sys, os, re, math, json, fnmatch
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
PCB  = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.kicad_pcb")
PRO  = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.kicad_pro")
PRETTY = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.pretty")
KFP  = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

SCALE = 10000.0          # mm -> DSN units, matching (resolution um 10)
def X(mm): return int(round(mm * SCALE))
def Y(mm): return int(round(-mm * SCALE))      # DSN is Y-up

# JLC wants 0.20 mm copper-to-edge; the outline tolerance is +/-0.2 mm. The DSN
# boundary is the only way to tell Freerouting about either, so inset by both.
EDGE_COPPER_MM = 0.30

def via_id(diameter, drill): return f"Via_{X(diameter)}_{X(drill)}"

# B.Cu window margin around the parts named by --bcu-under. Wide enough that a
# track can drop through, run clear of the pin field and climb back.
BCU_WINDOW_MARGIN = 6.0


def windows_for(b, refs):
    """bounding box of each named part's pads, grown by BCU_WINDOW_MARGIN"""
    out = []
    for ref in refs:
        pads = [pd for p in b.parts if p["ref"] == ref for pd in pad_xy(p)]
        if not pads:
            # A window built from the footprint ORIGIN instead of its pads came
            # out 12 mm square for a socket whose pin field is 48 mm long, and
            # the check that should have caught it passed vacuously over an
            # empty pad list. Refuse instead.
            raise SystemExit(f"  {ref}: no pads found -- cannot size a B.Cu window")
        xs = [q[0] for q in pads]
        ys = [q[1] for q in pads]
        out.append((min(xs) - BCU_WINDOW_MARGIN, min(ys) - BCU_WINDOW_MARGIN,
                    max(xs) + BCU_WINDOW_MARGIN, max(ys) + BCU_WINDOW_MARGIN))
    # merge overlapping windows so the complement stays simple
    merged = []
    for w in sorted(out):
        if merged and w[0] <= merged[-1][2] and not (w[3] < merged[-1][1] or w[1] > merged[-1][3]):
            m = merged[-1]
            merged[-1] = (min(m[0], w[0]), min(m[1], w[1]), max(m[2], w[2]), max(m[3], w[3]))
        else:
            merged.append(w)
    return merged


def pad_xy(p):
    blk = p.get("blk")
    out = []
    for m in re.finditer(r'\(pad "', blk or ""):
        pb = sexp(blk, m.start())
        am = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
        if am:
            px, py = float(am.group(1)), float(am.group(2))
            th = math.radians(p["rot"]); cs, sn = math.cos(th), math.sin(th)
            out.append((p["x"] + px * cs + py * sn, p["y"] - px * sn + py * cs))
    return out


def npth_holes(b):
    """Every non-plated hole, in board coordinates: (ref, x, y, drill).

    A mounting hole carries no net, so it is correctly absent from the netlist
    and from every image -- the pin parser drops `np_thru_hole` with the comment
    "mechanical only", which is right about what it IS and wrong about what it
    DOES. It is still a drill, and a drill through a trace cuts the trace.

    Freerouting cannot infer this. The DSN has no way to say "hole", so unless
    one is fenced explicitly the router sees empty board and routes across it.
    It did: VBAT crossed BT1's bolt hole at (89.345, 43.550) TWICE, at 0.000 mm
    against a 0.25 mm rule, on 19.3 mm and 10.5 mm segments. DRC found it after
    import; nothing could have found it before.

    Six holes are invisible without this -- H1-H4 at the corners, where little
    routes anyway, and BT1's two bolt holes, which sit mid-board inside the
    battery's own copper.
    """
    out = []
    for p in b.parts:
        blk = p.get("blk") or ""
        for m in re.finditer(r'\(pad "', blk):
            pb = sexp(blk, m.start())
            kind = re.match(r'\(pad "[^"]*" (\S+)', pb)
            if not kind or kind.group(1) != "np_thru_hole":
                continue
            am = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
            dr = re.search(r"\(drill ([-\d.]+)\)", pb)
            if not (am and dr):
                continue
            px, py = float(am.group(1)), float(am.group(2))
            th = math.radians(p["rot"])
            cs, sn = math.cos(th), math.sin(th)
            out.append((p["ref"], p["x"] + px * cs + py * sn,
                        p["y"] - px * sn + py * cs, float(dr.group(1))))
    return out


def complement_rects(board, windows):
    """the board minus the windows, as axis-aligned rectangles"""
    x0, y0, x1, y1 = board
    if not windows: return [(x0, y0, x1, y1)]
    rects = []
    xs = sorted({x0, x1} | {v for w in windows for v in (w[0], w[2])})
    ys = sorted({y0, y1} | {v for w in windows for v in (w[1], w[3])})
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i+1]) / 2, (ys[j] + ys[j+1]) / 2
            if any(w[0] <= cx <= w[2] and w[1] <= cy <= w[3] for w in windows): continue
            rects.append((xs[i], ys[j], xs[i+1], ys[j+1]))
    return rects


def sexp(text, start):
    d = 0; i = start; instr = False
    while i < len(text):
        c = text[i]
        if instr:
            if c == "\\": i += 2; continue
            if c == '"': instr = False
        elif c == '"': instr = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return text[start:i + 1]
        i += 1
    raise ValueError("unbalanced s-expression")


def load_footprint(libid):
    lib, name = libid.split(":", 1)
    base = PRETTY if lib == "caryatid" else os.path.join(KFP, lib + ".pretty")
    return open(os.path.join(base, name + ".kicad_mod")).read()


class Pcb:
    def __init__(self):
        self.t = open(PCB).read()
        self.nets = {int(m.group(1)): m.group(2)
                     for m in re.finditer(r'^\t\(net (\d+) "([^"]*)"\)', self.t, re.M)}
        self.parts = list(self._parts())
        self.outline = self._outline()

    def _outline(self):
        pts = []
        for m in re.finditer(r"\(gr_line", self.t):
            blk = sexp(self.t, m.start())
            if '"Edge.Cuts"' not in blk: continue
            s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            pts.append(((float(s.group(1)), float(s.group(2))),
                        (float(e.group(1)), float(e.group(2)))))
        xs = [p[0] for seg in pts for p in seg]; ys = [p[1] for seg in pts for p in seg]
        return (min(xs), min(ys), max(xs), max(ys))

    def _parts(self):
        for m in re.finditer(r"^\t\(footprint \"([^\"]+)\"", self.t, re.M):
            blk = sexp(self.t, m.start() + 1)
            at = re.search(r"^\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk, re.M)
            lay = re.search(r"^\t\t\(layer \"([^\"]+)\"", blk, re.M)
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
            val = re.search(r'\(property "Value" "([^"]*)"', blk)
            pads = {}
            for pm in re.finditer(r'\(pad "', blk):
                pb = sexp(blk, pm.start())
                num = re.match(r'\(pad "([^"]*)"', pb).group(1)
                nm = re.search(r'\(net (\d+) "([^"]*)"\)', pb)
                if nm: pads[num] = nm.group(2)
            yield {"blk": blk,
                   "lib": m.group(1), "ref": ref.group(1) if ref else "?",
                   "val": val.group(1) if val else "",
                   "x": float(at.group(1)), "y": float(at.group(2)),
                   "rot": float(at.group(3) or 0),
                   "back": (lay.group(1) == "B.Cu") if lay else False,
                   "netof": pads}

    def tracks(self):
        for m in re.finditer(r"^\t\(segment", self.t, re.M):
            b = sexp(self.t, m.start() + 1)
            s = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
            w = re.search(r"\(width ([-\d.]+)\)", b)
            l = re.search(r'\(layer "([^"]+)"\)', b)
            n = re.search(r"\(net (\d+)\)", b)
            if s and e and w and l and n:
                yield (float(s.group(1)), float(s.group(2)), float(e.group(1)),
                       float(e.group(2)), float(w.group(1)), l.group(1),
                       self.nets.get(int(n.group(1)), ""))

    def vias(self):
        for m in re.finditer(r"^\t\(via", self.t, re.M):
            b = sexp(self.t, m.start() + 1)
            a = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", b)
            s = re.search(r"\(size ([-\d.]+)\)", b)
            d = re.search(r"\(drill ([-\d.]+)\)", b)
            n = re.search(r"\(net (\d+)\)", b)
            if a and s and d and n:
                yield (float(a.group(1)), float(a.group(2)), float(s.group(1)),
                       float(d.group(1)), self.nets.get(int(n.group(1)), ""))


def pad_xy_one(p, num):
    """placed centre of one pad of a footprint"""
    blk = p.get("blk")
    if not blk: return None
    for m in re.finditer(r'\(pad "', blk):
        pb = sexp(blk, m.start())
        if re.match(r'\(pad "([^"]*)"', pb).group(1) != num: continue
        am = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pb)
        if not am: return None
        px, py = float(am.group(1)), float(am.group(2))
        th = math.radians(p["rot"]); cs, sn = math.cos(th), math.sin(th)
        return (p["x"] + px * cs + py * sn, p["y"] - px * sn + py * cs)
    return None


def image_of(libid):
    """canonical image: pads from the LIBRARY footprint, unrotated and unmirrored"""
    t = load_footprint(libid)
    pads = []
    for m in re.finditer(r'\(pad "', t):
        b = sexp(t, m.start())
        head = b[:140]
        num = re.match(r'\(pad "([^"]*)"', b).group(1)
        kind = re.match(r'\(pad "[^"]*" (\S+) (\S+)', b)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", b)
        sz = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", b)
        dr = re.search(r"\(drill ([-\d.]+)\)", b)
        if not (at and sz and kind): continue
        if kind.group(1) == "np_thru_hole": continue          # mechanical only
        pads.append({"num": num, "type": kind.group(1), "shape": kind.group(2),
                     "x": float(at.group(1)), "y": float(at.group(2)),
                     "w": float(sz.group(1)), "h": float(sz.group(2)),
                     "drill": float(dr.group(1)) if dr else None})
    return pads


def padstack_id(p):
    tag = "T" if p["type"] == "thru_hole" else "S"
    if p["shape"] == "circle":
        return f"{tag}_C_{p['w']:.3f}".replace(".", "_")
    return f"{tag}_R_{p['w']:.3f}x{p['h']:.3f}".replace(".", "_")


def padstack_def(pid, p):
    layers = ["F.Cu", "B.Cu"] if p["type"] == "thru_hole" else ["F.Cu"]
    out = [f"    (padstack {pid}"]
    for L in layers:
        if p["shape"] == "circle":
            out.append(f"      (shape (circle {L} {X(p['w'])}))")
        else:   # rect / roundrect / oval -- rect is the conservative envelope
            out.append(f"      (shape (rect {L} {X(-p['w']/2)} {Y(p['h']/2)} "
                       f"{X(p['w']/2)} {Y(-p['h']/2)}))")
    out.append("      (attach off)")
    out.append("    )")
    return "\n".join(out)


def main():
    both_layers = "--both-layers" in sys.argv
    bcu_under = []
    if "--bcu-under" in sys.argv:
        bcu_under = sys.argv[sys.argv.index("--bcu-under") + 1].split(",")
    args = sys.argv[1:]
    with_gnd = "--with-gnd" in args
    out_path = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.dsn")
    if "-o" in args: out_path = args[args.index("-o") + 1]

    b = Pcb()
    rules = json.load(open(PRO))["net_settings"]
    default = next(c for c in rules["classes"] if c["name"] == "Default")
    byname = {c["name"]: c for c in rules["classes"]}

    x0, y0, x1, y1 = b.outline
    x0 += EDGE_COPPER_MM; y0 += EDGE_COPPER_MM
    x1 -= EDGE_COPPER_MM; y1 -= EDGE_COPPER_MM

    # ---- library: one image per footprint, one padstack per distinct pad ----
    images, stacks = OrderedDict(), OrderedDict()
    for p in b.parts:
        if p["lib"] in images: continue
        pads = image_of(p["lib"])
        if not pads: continue
        images[p["lib"]] = pads
        for pd in pads:
            stacks.setdefault(padstack_id(pd), pd)

    L = []
    L.append('(pcb caryatid')
    L.append('  (parser')
    L.append('    (string_quote ")')
    L.append('    (space_in_quoted_tokens on)')
    L.append('    (host_cad "caryatid tools/export_dsn.py")')
    L.append('    (host_version "1")')
    L.append('  )')
    L.append('  (resolution um 10)')
    L.append('  (unit um)')
    L.append('  (structure')
    L.append('    (layer F.Cu (type signal) (property (index 0)))')
    if both_layers or bcu_under:
        L.append('    (layer B.Cu (type signal) (property (index 1)))')
    # else B.Cu is not declared a signal layer at all, so the router cannot put
    # anything on it. That is the honest model when B.Cu is a ground plane: the
    # last route placed ~130 tracks there, cut the plane into 13 islands and
    # produced three hole_clearance violations. A route that succeeds by
    # shredding the return path reports a placement as fine when it is not.
    L.append(f'    (boundary (rect pcb {X(x0)} {Y(y1)} {X(x1)} {Y(y0)}))')
    if bcu_under:
        # B.Cu is a ground plane EXCEPT under these parts. 40 header pins at
        # 2.54 mm leave exactly one 0.25 mm channel between neighbours, so on one
        # layer the Seed sockets alone accounted for 29 of 83 unrouted. This
        # gives them a second layer precisely where the congestion is, and fences
        # the rest of the back off so the plane stays whole under the switcher
        # and the audio section.
        wins = windows_for(b, bcu_under)
        for r in complement_rects((x0, y0, x1, y1), wins):
            L.append(f'    (keepout "" (rect B.Cu {X(r[0])} {Y(r[3])} {X(r[2])} {Y(r[1])}))')
            L.append(f'    (via_keepout "" (rect B.Cu {X(r[0])} {Y(r[3])} {X(r[2])} {Y(r[1])}))')
        print(f"  B.Cu open only under {', '.join(bcu_under)}: "
              f"{len(wins)} window(s), {len(complement_rects((x0,y0,x1,y1), wins))} keepouts")

    # Non-plated holes, fenced on BOTH layers. See npth_holes() for why they are
    # invisible otherwise. The diameter is the drill plus the board's own
    # hole-clearance rule on each side, which is exactly what DRC measures --
    # hole edge to track edge. If Freerouting additionally keeps its own
    # clearance from a keepout then this is conservative, which is the right
    # direction to be wrong in for a hole that would cut a trace.
    holes = npth_holes(b)
    if holes:
        hclr = json.load(open(PRO))["board"]["design_settings"]["rules"]["min_hole_clearance"]
        for ref, hx, hy, drill in holes:
            dia = drill + 2 * hclr
            for layer in ("F.Cu", "B.Cu"):
                L.append(f'    (keepout "" (circle {layer} {X(dia)} {X(hx)} {Y(hy)}))')
                L.append(f'    (via_keepout "" (circle {layer} {X(dia)} {X(hx)} {Y(hy)}))')
        print(f"  fenced {len(holes)} non-plated hole(s) at drill + 2 x {hclr} mm: "
              + ", ".join(sorted({r for r, _, _, _ in holes})))

    L.append(f'    (via "Via_{X(default["via_diameter"])}_{X(default["via_drill"])}")')
    L.append('    (rule')
    L.append(f'      (width {X(default["track_width"])})')
    L.append(f'      (clearance {X(default["clearance"])})')
    L.append(f'      (clearance {X(default["clearance"])} (type default_smd))')
    L.append(f'      (clearance {X(default["clearance"])} (type smd_smd))')
    L.append('    )')
    L.append('  )')

    # ---- placement ----------------------------------------------------------
    L.append('  (placement')
    bylib = OrderedDict()
    for p in b.parts:
        if p["lib"] in images: bylib.setdefault(p["lib"], []).append(p)
    for lib, parts in bylib.items():
        L.append(f'    (component "{lib}"')
        for p in parts:
            side = "back" if p["back"] else "front"
            rot = p["rot"] % 360
            L.append(f'      (place "{p["ref"]}" {X(p["x"])} {Y(p["y"])} {side} {rot:g}'
                     f' (PN "{p["val"]}"))')
        L.append('    )')
    L.append('  )')

    # ---- library ------------------------------------------------------------
    L.append('  (library')
    for lib, pads in images.items():
        L.append(f'    (image "{lib}"')
        for pd in pads:
            L.append(f'      (pin {padstack_id(pd)} "{pd["num"]}" {X(pd["x"])} {Y(pd["y"])})')
        L.append('    )')
    for pid, pd in stacks.items():
        L.append(padstack_def(pid, pd))
    d = default
    for vd, vdr in sorted({(c["via_diameter"], c["via_drill"]) for c in rules["classes"]}):
        L.append(f'    (padstack "{via_id(vd, vdr)}"')
        L.append(f'      (shape (circle F.Cu {X(vd)}))')
        L.append(f'      (shape (circle B.Cu {X(vd)}))')
        L.append('      (attach off)')
        L.append('    )')
    L.append('  )')

    # ---- network ------------------------------------------------------------
    pins = {}
    for p in b.parts:
        for num, net in p["netof"].items():
            if not net: continue
            pins.setdefault(net, []).append(f'{p["ref"]}-{num}')
    # Nets that are poured as copper zones are already connected by that zone.
    # Emitting them here makes the router lay a redundant track alongside the
    # pour, or fail trying -- and those were among the hardest nets, which is the
    # whole reason for pouring them.
    # A pour connects the pads INSIDE it and nothing else. Dropping the whole net
    # from the DSN -- which this did at first -- left every pad outside the pour
    # unconnected for good: +5V_RAW still had to reach R7 and FB1, VOUT had J4
    # and C3, EN_SW had J3. Only /power/SW was genuinely complete.
    #
    # So instead of hiding the net, tell the router what the pour already joins,
    # as protected wiring between those pads. It then routes only the remainder.
    pour_pads = {}
    for m in re.finditer(r"^\t\(zone", b.t, re.M):
        z = sexp(b.t, m.start() + 1)
        nm = re.search(r'\(net_name "([^"]*)"\)', z)
        pr = re.search(r"\(priority (\d+)\)", z)
        if not (nm and nm.group(1) and pr and int(pr.group(1)) > 0): continue
        net = nm.group(1)
        pm = re.search(r"\(polygon", z)
        poly = [(float(u), float(v)) for u, v in
                re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", sexp(z, pm.start()))]
        def inside(q):
            x, y = q; c = False
            for i in range(len(poly)):
                x0, y0 = poly[i]; x1, y1 = poly[(i+1) % len(poly)]
                if (y0 > y) != (y1 > y):
                    if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
            return c
        for p_ in b.parts:
            for num, n2 in p_["netof"].items():
                if n2 != net: continue
                q = pad_xy_one(p_, num)
                if q and inside(q):
                    pour_pads.setdefault(net, []).append((f'{p_["ref"]}-{num}', q))
    if pour_pads:
        for net, lst in sorted(pour_pads.items()):
            allp = sum(1 for p_ in b.parts for n2 in p_["netof"].values() if n2 == net)
            print(f"  pour on {net}: joins {len(lst)} of {allp} pads"
                  + ("  (complete)" if len(lst) == allp else "  (rest still routed)"))
    poured = set()

    skipped = []
    emitted = []
    L.append('  (network')
    for net, pl in sorted(pins.items()):
        if net == "GND" and not with_gnd:
            skipped.append(net); continue
        if net in poured:
            skipped.append(net); continue
        if len(pl) < 2: continue
        L.append(f'    (net "{net}"')
        L.append('      (pins ' + " ".join(sorted(pl)) + ')')
        L.append('    )')
        emitted.append(net)

    # One class per netclass, carrying its own width, clearance and via. Emitting
    # only Default sent every net out at 0.25 mm -- see the header.
    members = OrderedDict((c["name"], []) for c in rules["classes"])
    ambiguous = []
    for net in emitted:
        hit = {p["netclass"] for p in rules.get("netclass_patterns", [])
               if fnmatch.fnmatchcase(net, p["pattern"])}
        if len(hit) > 1:
            # Precedence between overlapping patterns is not something to guess
            # at. Today nothing overlaps; if that changes, say so rather than
            # silently pick one.
            ambiguous.append((net, sorted(hit)))
        members[hit.pop() if len(hit) == 1 else "Default"].append(net)
    if ambiguous:
        for net, hit in ambiguous:
            print(f"  ERROR net {net} matches {', '.join(hit)} -- precedence undefined")
        sys.exit(1)

    # KiCad's own export names the default class `kicad_default` and gives it a
    # single empty member; everything unlisted falls into it. Naming it "Default"
    # and listing all 72 nets explicitly parsed fine but Freerouting applied none
    # of the widths -- every new segment came back at the default 0.25 mm. Follow
    # the convention the router is actually tested against.
    for name, nets in members.items():
        c = byname[name]
        if name == "Default":
            head = '    (class kicad_default ""'
        else:
            head = f'    (class {name} ' + " ".join(f'"{n}"' for n in nets)
        L.append(head.rstrip())
        L.append(f'      (circuit (use_via "{via_id(c["via_diameter"], c["via_drill"])}"))')
        L.append(f'      (rule (width {X(c["track_width"])}) (clearance {X(c["clearance"])}))')
        L.append('    )')
    L.append('  )')

    # ---- wiring: existing copper, protected ---------------------------------
    L.append('  (wiring')
    nseg = nvia = 0
    # what each pour already joins, as protected wiring, so the router treats
    # those pads as connected and spends its effort on the pads outside
    npour = 0
    for net, lst in sorted(pour_pads.items()):
        if net == "GND" and not with_gnd: continue
        pts = [q for _, q in lst]
        ins, out = [0], list(range(1, len(pts)))
        while out:
            i, j = min(((a, c) for a in ins for c in out),
                       key=lambda e: math.dist(pts[e[0]], pts[e[1]]))
            L.append(f'    (wire (path F.Cu {X(0.25)} {X(pts[i][0])} {Y(pts[i][1])} '
                     f'{X(pts[j][0])} {Y(pts[j][1])}) (net "{net}") (type protect))')
            ins.append(j); out.remove(j); npour += 1
    for sx, sy, ex, ey, w, layer, net in b.tracks():
        if not net: continue
        L.append(f'    (wire (path {layer} {X(w)} {X(sx)} {Y(sy)} {X(ex)} {Y(ey)})'
                 f' (net "{net}") (type protect))')
        nseg += 1
    for vx, vy, size, drill, net in b.vias():
        if not net: continue
        L.append(f'    (via "Via_{X(d["via_diameter"])}_{X(d["via_drill"])}"'
                 f' {X(vx)} {Y(vy)} (net "{net}") (type protect))')
        nvia += 1
    L.append('  )')
    L.append(')')

    text = "\n".join(L) + "\n"

    # structural self-check -- this is never loaded by Freerouting here
    depth = 0
    for ch in text:
        if ch == "(": depth += 1
        elif ch == ")": depth -= 1
        if depth < 0: raise SystemExit("unbalanced output")
    if depth != 0: raise SystemExit(f"unbalanced output, depth {depth}")

    open(out_path, "w").write(text)
    # count what was actually emitted, not what was eligible -- this recomputed
    # the filter independently and so kept reporting 95 after three nets were
    # dropped to pours
    routed = len(emitted)
    print(f"wrote {out_path}")
    print(f"  board      {x1-x0:.1f} x {y1-y0:.1f} mm")
    print(f"  components {len(b.parts)}   images {len(images)}   padstacks {len(stacks)}")
    print(f"  nets to route {routed}" + (f"   ({len(skipped)} skipped: plane + pours)" if skipped else ""))
    print(f"  protected  {nseg} tracks, {nvia} vias"
          + (f", {npour} pour links" if npour else ""))
    print(f"  parens balanced")
    return 0


if __name__ == "__main__":
    sys.exit(main())