#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check hardware/pcb/caryatid.kicad_pcb against the constraints KiCad's DRC does not.

    python3 tools/check_board.py            # report
    python3 tools/check_board.py --check    # exit 1 on any failure (for CI)

Every layout fault found by hand during the first spin had the same shape: a check
that modelled one thing and silently ignored another. Each is a class here.

  1 front courtyard overlap, INCLUDING the M3 mounting holes -- omitting them
    passed a board with two connectors sitting on top of one
  2 back courtyard overlap
  3 back parts over front through-hole pads -- a PTH pad occupies every copper
    layer, so it is a keepout for the opposite face. Omitting this put 29 parts
    on the Seed's socket pads
  4 everything inside the outline, with edge clearance
  5 component height vs standoff, per face -- C7 is 5.4 mm on the back and does
    not clear a 4 mm standoff. Nothing in KiCad checks this
 5b front height vs the ENCLOSURE CEILING -- check 5 asks what clears the
    standoff below, and for a while nothing asked what clears the lid above, so
    the front heights sat in the table unused. BT1 at 21.31 mm sets the stack
  6 via annular ring vs the fab floor -- the project rule was set BELOW JLC's
    0.18 mm, so DRC reported a pass on vias the fab would reject
  7 track width vs the pitch of the pad it leaves -- 0.8 mm copper leaving a
    0.5 mm-pitch package shorts to the neighbouring pad
  8 silkscreen height and stroke vs JLC's floors
  9 a series part (diode, ferrite, inductor, fuse) carries ONE current, so the
    nets either side of it must be in the same netclass. /power/DC_IN was in
    Default at 0.25 mm while VIN_DC, across D1 from it, was HighCurrent at 1.20

Geometry rules established by reading KiCad-written boards, not assumed:
  * rotation is applied at compute time; stored pad coords are PRE-rotation
  * a back-side footprint stores its geometry Y-NEGATED, layers swapped
"""
import sys, os, re, math, json

HERE = os.path.dirname(os.path.abspath(__file__))
PCB  = os.environ.get("CARYATID_PCB") or os.path.join(HERE, "..", "hardware", "pcb", "caryatid.kicad_pcb")
PRO  = os.path.join(HERE, "..", "hardware", "pcb", "caryatid.kicad_pro")

# --- fab and mechanical limits ----------------------------------------------
JLC_ANNULAR_MIN   = 0.18   # 1 oz PTH, absolute minimum (0.25 recommended)
JLC_SILK_HEIGHT   = 0.8
JLC_SILK_STROKE   = 0.15
EDGE_CLEARANCE    = 0.5
COURTYARD_GAP     = 0.0    # courtyards may touch, not overlap
STANDOFF_MM       = 2.0    # The back face is empty -- every component is on the
                           # front -- so the standoff only has to clear solder
                           # joints. It was 7 mm when C7 (5.4 mm) hung underneath.
                           # This is the ELECTRICAL minimum, not the build spec.
BUILD_STANDOFF_MM = 4.0    # What actually gets fitted. Costs 2 mm of headroom.
PCB_THICKNESS_MM  = 1.6

# Interior heights. The BUD is the binding case, not the phone. Its figure is
# DERIVED from local/reference/CU-477.STEP (loa), not measured: 38.10 mm external
# with a 1.98 mm wall given independently by the base and the cover solids, so
# 38.10 - 2 x 1.98 = 34.14. A plane 1.60 mm proud of the floor would leave 32.54
# if the standoffs seat on it rather than on the floor.
ENCLOSURES = {"BUD CU-477": 34.14, "telephone shell": 40.0}

# Heights are not in the footprint files. Most encode it in the name; the rest
# are from the datasheets. A part missing here is reported, not assumed safe.
HEIGHTS = {
    "CP_Elec_6.3x5.4": 5.4, "D_SMA": 2.3,
    "L_Vishay_IFSC-1515AH_4x4x1.8mm": 1.8,
    "SOIC-14_3.9x8.7mm_P1.27mm": 1.75, "SOIC-8_3.9x4.9mm_P1.27mm": 1.75,
    "C_0805_2012Metric": 1.35, "L_0805_2012Metric": 1.2,
    "C_0603_1608Metric": 0.95, "R_0603_1608Metric": 0.55,
    "SOT-563": 0.6, "BQ24074RGT_QFN-16-1EP_3x3mm_P0.5mm": 1.0,
    "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal": 1.35,
    # front side -- checked against the enclosure ceiling by check 5b
    "BatteryHolder_MPD_BH-18650-PC": 21.31,
    "DaisySeed_Socket_A_1x20": 8.5, "DaisySeed_Socket_B_1x20": 8.5,
    "IDC-Header_2x05_P2.54mm_Vertical": 9.0,
    "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical": 5.75,
    "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical": 5.75,
    "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical": 5.75,
    "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical": 5.75,
    "PinHeader_2x04_P2.54mm_Vertical": 8.5,
    "MountingHole_3.2mm_M3": 0.0,
}

# Height with the thing that plugs INTO it fitted. The socket alone is 8.5 mm;
# the Seed sitting in it reaches 10.5. Check 5b uses these in preference, because
# the lid has to clear the assembly, not the bare footprint.
ASSEMBLED = {
    "DaisySeed_Socket_A_1x20": 10.5, "DaisySeed_Socket_B_1x20": 10.5,
}

def sexp(text, start):
    """text of the s-expression beginning at text[start] == '('"""
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


class Board:
    def __init__(self, path):
        self.t = open(path).read()
        self.origin = self._origin()
        self.outline = self._outline()
        self.parts = list(self._parts())

    def _outline(self):
        xs, ys = [], []
        for m in re.finditer(r"\(gr_line", self.t):
            blk = sexp(self.t, m.start())
            if '"Edge.Cuts"' not in blk: continue
            for mm in re.finditer(r"\((?:start|end) ([-\d.]+) ([-\d.]+)\)", blk):
                xs.append(float(mm.group(1))); ys.append(float(mm.group(2)))
        return (min(xs), min(ys), max(xs), max(ys))

    def _origin(self):
        return (0.0, 0.0)   # everything is reported in page coordinates

    def _parts(self):
        for m in re.finditer(r"^\t\(footprint \"([^\"]+)\"", self.t, re.M):
            blk = sexp(self.t, m.start() + 1)
            am  = re.search(r"^\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk, re.M)
            lm  = re.search(r"^\t\t\(layer \"([^\"]+)\"", blk, re.M)
            rm  = re.search(r"\(property \"Reference\" \"([^\"]+)\"", blk)
            yield {
                "lib": m.group(1), "name": m.group(1).split(":", 1)[-1],
                "ref": rm.group(1) if rm else "?",
                "x": float(am.group(1)), "y": float(am.group(2)),
                "rot": float(am.group(3) or 0),
                "back": (lm.group(1) == "B.Cu") if lm else False,
                "blk": blk,
            }

    @staticmethod
    def _xform(p, px, py):
        """pad/graphic local -> page. Rotation is applied here (KiCad stores it
        pre-rotation); a back footprint stores geometry already Y-negated."""
        th = math.radians(p["rot"]); cs, sn = math.cos(th), math.sin(th)
        return (p["x"] + px * cs + py * sn, p["y"] - px * sn + py * cs)

    def courtyard(self, p):
        xs, ys = [], []
        want = "B.CrtYd" if p["back"] else "F.CrtYd"
        for m in re.finditer(r"\(fp_(?:line|poly|rect|circle|arc)", p["blk"]):
            blk = sexp(p["blk"], m.start())
            if f'"{want}"' not in blk: continue
            for mm in re.finditer(r"\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)", blk):
                xs.append(float(mm.group(1))); ys.append(float(mm.group(2)))
        if not xs:
            return None
        corners = [self._xform(p, x, y) for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        return (min(c[0] for c in corners), min(c[1] for c in corners),
                max(c[0] for c in corners), max(c[1] for c in corners))

    def pads(self, p, tht_only=False):
        out = []
        for m in re.finditer(r"\(pad \"", p["blk"]):
            blk = sexp(p["blk"], m.start())
            head = blk[:120]
            if tht_only and "thru_hole" not in head: continue
            am = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
            sm = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", blk)
            if not (am and sm): continue
            num = re.match(r'\(pad "([^"]*)"', blk).group(1)
            w, h = float(sm.group(1)), float(sm.group(2))
            if p["rot"] in (90, 270): w, h = h, w
            cx, cy = self._xform(p, float(am.group(1)), float(am.group(2)))
            dm = re.search(r"\(drill ([-\d.]+)\)", blk)
            nm = re.search(r'\(net \d+ "([^"]*)"\)', blk)
            cm = re.search(r"\(clearance ([\d.]+)\)", blk)
            out.append({"num": num, "x": cx, "y": cy, "w": w, "h": h,
                        "drill": float(dm.group(1)) if dm else None,
                        "net": nm.group(1) if nm else None,
                        "smd": "smd" in head,
                        "clear": float(cm.group(1)) if cm else None,
                        "span": (m.start(), m.start() + len(blk))})
        return out


def overlaps(a, b, gap=0.0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or
                a[3] + gap <= b[1] or b[3] + gap <= a[1])


def main():
    strict = "--check" in sys.argv
    B = Board(PCB)
    x0, y0, x1, y1 = B.outline
    fails = []
    def fail(cls, msg): fails.append((cls, msg))

    front = [p for p in B.parts if not p["back"]]
    back  = [p for p in B.parts if p["back"]]

    # 1 + 2 -- courtyard overlap within each face. Mounting holes are footprints
    # here, so they are included automatically; omitting them was the original bug.
    for label, group in (("front", front), ("back", back)):
        boxes = [(p["ref"], B.courtyard(p)) for p in group]
        boxes = [(r, c) for r, c in boxes if c]
        for i, (ra, ca) in enumerate(boxes):
            for rb, cb in boxes[i + 1:]:
                if overlaps(ca, cb, COURTYARD_GAP):
                    fail(f"{label}-overlap", f"{ra} and {rb} courtyards overlap")

    # 3 -- back parts vs front through-hole pads (a PTH pad is on every layer)
    keep = []
    for p in front:
        for pad in B.pads(p, tht_only=True):
            keep.append((p["ref"], pad["num"],
                         (pad["x"] - pad["w"] / 2 - 0.25, pad["y"] - pad["h"] / 2 - 0.25,
                          pad["x"] + pad["w"] / 2 + 0.25, pad["y"] + pad["h"] / 2 + 0.25)))
    for p in back:
        c = B.courtyard(p)
        if not c: continue
        for ref, num, box in keep:
            if overlaps(c, box):
                fail("back-over-pth", f"{p['ref']} sits over {ref} pad {num}")

    # 4 -- inside the outline
    for p in B.parts:
        c = B.courtyard(p)
        if not c: continue
        if (c[0] < x0 + EDGE_CLEARANCE or c[1] < y0 + EDGE_CLEARANCE or
                c[2] > x1 - EDGE_CLEARANCE or c[3] > y1 - EDGE_CLEARANCE):
            fail("outline", f"{p['ref']} is outside the outline or inside its {EDGE_CLEARANCE} mm margin")

    # 5 -- height vs standoff, back face only. Nothing in KiCad checks this.
    for p in back:
        h = HEIGHTS.get(p["name"])
        if h is None:
            fail("height-unknown", f"{p['ref']} ({p['name']}) has no recorded height")
        elif h > STANDOFF_MM:
            fail("height", f"{p['ref']} is {h} mm on the back, over the {STANDOFF_MM} mm standoff")

    # 5b -- front height vs the enclosure ceiling.
    #
    # Check 5 asks whether a part clears the standoff underneath. Nothing asked
    # whether a part clears the LID, so the front heights above were recorded and
    # then never compared to anything -- the comment in HEIGHTS said as much. That
    # is the same shape as every other miss on this board: a check that models one
    # thing and silently ignores another. BT1 at 21.31 mm sets the stack, and the
    # BUD's 34.14 mm interior is the binding case, not the phone's 40+.
    enc, interior = min(ENCLOSURES.items(), key=lambda kv: kv[1])
    for p in front:
        h = ASSEMBLED.get(p["name"], HEIGHTS.get(p["name"]))
        if h is None:
            fail("height-unknown", f"{p['ref']} ({p['name']}) has no recorded height")
            continue
        stack = BUILD_STANDOFF_MM + PCB_THICKNESS_MM + h
        if stack > interior:
            fail("ceiling", f"{p['ref']} stacks to {stack:.2f} mm, over {enc}'s {interior} mm interior")

    # 6 -- via annular ring
    for m in re.finditer(r"^\t\(via", B.t, re.M):
        blk = sexp(B.t, m.start() + 1)
        s = re.search(r"\(size ([-\d.]+)\)", blk); d = re.search(r"\(drill ([-\d.]+)\)", blk)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", blk)
        if not (s and d): continue
        ring = (float(s.group(1)) - float(d.group(1))) / 2
        if ring < JLC_ANNULAR_MIN:
            fail("annular", f"via at ({at.group(1)}, {at.group(2)}) ring {ring:.3f} < {JLC_ANNULAR_MIN}")
    for p in B.parts:                                   # in-footprint vias too
        for pad in B.pads(p):
            if pad["drill"] and pad["w"] == pad["h"]:
                ring = (pad["w"] - pad["drill"]) / 2
                if ring < JLC_ANNULAR_MIN and pad["drill"] < 1.0:
                    fail("annular", f"{p['ref']} pad {pad['num']} ring {ring:.3f} < {JLC_ANNULAR_MIN}")

    # 6b -- netclass via defaults. The checker originally only inspected vias that
    # already existed, so a netclass whose default via is below the fab floor went
    # unnoticed until an autorouter would have placed hundreds of them.
    try:
        import json as _json
        for c in _json.load(open(PRO))["net_settings"]["classes"]:
            dia, dr = c.get("via_diameter"), c.get("via_drill")
            if dia is None or dr is None: continue
            if (dia - dr) / 2 < JLC_ANNULAR_MIN:
                fail("annular-netclass",
                     f"netclass {c['name']} default via {dia}/{dr} -> ring {(dia-dr)/2:.3f}")
    except Exception as e:
        fail("annular-netclass", f"could not read netclass vias: {e}")

    # 7 -- track width vs the pitch of the pad it starts on
    padindex = []
    for p in B.parts:
        pads = B.pads(p)
        for a in pads:
            near = [math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in pads if b is not a]
            padindex.append((a, min(near) if near else 99.0, p["ref"]))
    for m in re.finditer(r"^\t\(segment", B.t, re.M):
        blk = sexp(B.t, m.start() + 1)
        st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
        w  = re.search(r"\(width ([-\d.]+)\)", blk)
        if not (st and w): continue
        sx, sy, tw = float(st.group(1)), float(st.group(2)), float(w.group(1))
        for pad, pitch, ref in padindex:
            if abs(pad["x"] - sx) < 0.05 and abs(pad["y"] - sy) < 0.05 and tw > pitch:
                fail("track-pitch", f"{tw} mm track leaves {ref} pad {pad['num']} on {pitch:.2f} mm pitch")

    # 8 -- silkscreen legibility
    for m in re.finditer(r"\((?:fp_text|gr_text|property) ", B.t):
        blk = sexp(B.t, m.start())
        lm = re.search(r"\(layer \"([^\"]+)\"", blk)
        if not lm or "SilkS" not in lm.group(1): continue
        if "(hide yes)" in blk: continue
        sm = re.search(r"\(size ([\d.]+) ([\d.]+)\)", blk)
        tm = re.search(r"\(thickness ([\d.]+)\)", blk)
        label = (re.search(r'"([^"]*)"', blk) or [None, "?"])[1]
        if sm and float(sm.group(1)) < JLC_SILK_HEIGHT:
            fail("silk-height", f'"{label}" is {sm.group(1)} mm, under JLC {JLC_SILK_HEIGHT}')
        if tm and float(tm.group(1)) < JLC_SILK_STROKE:
            fail("silk-stroke", f'"{label}" stroke {tm.group(1)} mm, under JLC {JLC_SILK_STROKE}')

    # 9 -- a series part must have the same netclass on both sides
    #
    # A diode, ferrite, inductor or fuse passes the SAME CURRENT through both
    # pads, so the nets either side of it belong in the same class. Two did not,
    # and nothing noticed until a human looked at the board: /power/DC_IN sat in
    # Default at 0.25 mm while VIN_DC, the other side of D1, was HighCurrent at
    # 1.20; and +5V_RAW sat in Default while +5V, the other side of FB1, was
    # Power at 0.80. Both because netclass patterns are literal names -- nothing
    # matched DC_IN, and "+5V" does not match "+5V_RAW" under fnmatch.
    try:
        import json as _json, fnmatch as _fn
        _pro = _json.load(open(PRO))["net_settings"]
        _cls = {c["name"]: c for c in _pro["classes"]}
        _pat = _pro.get("netclass_patterns", [])
        def _k(n):
            h = {q["netclass"] for q in _pat if _fn.fnmatchcase(n, q["pattern"])}
            return h.pop() if len(h) == 1 else "Default"
        for p in B.parts:
            if not re.match(r"(D|L|FB|F)\d+$", p["ref"]): continue
            pads = [pd for pd in B.pads(p) if pd["net"]]
            nets = {pd["net"] for pd in pads}
            if len(nets) != 2: continue
            a, b = sorted(nets)
            ka, kb = _k(a), _k(b)
            if ka != kb:
                wa, wb = _cls[ka]["track_width"], _cls[kb]["track_width"]
                fail("series-netclass",
                     f"{p['ref']} passes one current but {a} is {ka} ({wa} mm) "
                     f"and {b} is {kb} ({wb} mm)")
    except Exception as e:
        fail("series-netclass", f"could not check series netclasses: {e}")

    # --- report -------------------------------------------------------------
    print(f"board {x1-x0:.1f} x {y1-y0:.1f} mm   "
          f"{len(front)} front / {len(back)} back   standoff {STANDOFF_MM} mm\n")
    if not fails:
        print("  all ten checks pass")
        return 0
    from collections import Counter
    for cls, n in Counter(c for c, _ in fails).most_common():
        print(f"  {n:>4}  {cls}")
        for c, msg in fails:
            if c == cls: print(f"          {msg}")
    print(f"\n  {len(fails)} problems")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())