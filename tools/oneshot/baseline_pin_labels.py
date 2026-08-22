#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Put each connector's pin labels on ONE baseline, justified to its outline.

    python3 tools/oneshot/baseline_pin_labels.py            # report
    python3 tools/oneshot/baseline_pin_labels.py --apply

WHAT IT DOES, AND WHERE IT REFUSES
-----------------------------------
pin_labels staggers labels into two or more rows when they will not fit at the
connector's pin pitch. That is correct and unavoidable, but where the text DOES
fit along the body a single row reads better: end labels pushed out to the silk
outline, inner labels left on the pad they name.

Measured before choosing, per connector, along the label axis:

    fits (11)     J1 J3 J6 J7 J8 J9 J10 J12 J14 J17 J18
    does not (4)  J4 J13 J15 J19
    excluded (3)  J5 J11 J16 -- two rows of pads, see FITS

J13 is 4.07 mm short along its body and J4 0.76. J15 and J19 miss by 0.06 mm,
which is only buyable by shrinking their text below their neighbours'. None of
those is a placement choice.

INNER LABELS STAY ON THEIR PAD, not evenly spaced. pin_labels exists so someone
tracing a wire can tell which pin is which; even spacing looks tidier and lets a
label drift off the pin it names, which costs the one thing the label is for.

THE BASELINE IS AN EXISTING ONE. Where labels are staggered across two columns,
this takes the column NEAREST the connector rather than computing a fresh
offset -- that position is already known to clear, and re-deriving it would risk
moving ink that DRC currently passes.

Results are LOCKED. pin_labels regenerates from its own model and a plain
--apply would otherwise revert this; --relock remains the deliberate override.

COLLECT FIRST, WRITE BACK TO FRONT. Editing the text inside a re.finditer loop
shifts every later offset and corrupts the file -- it raised `unbalanced
s-expression` on the first attempt at J1, and cycle.py's strip_copper carries
the same warning.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import check_board as C
import pin_labels as P

# Single-row connectors whose labels fit end-to-end along the body. Two-row
# parts (J5, J11, J16 -- IDC 2x5 and the 2x4 header) are EXCLUDED: their two
# label columns are one per PAD ROW, not a stagger to make text fit, and merging
# them would be wrong rather than tidier.
FITS = ["J1", "J3", "J6", "J7", "J8", "J9", "J10", "J12", "J14", "J17", "J18"]


def silk_pts(B, p):
    out = []
    for m in re.finditer(r"\(fp_(?:line|rect|poly|circle|arc)", p["blk"]):
        blk = C.sexp(p["blk"], m.start())
        if '"F.SilkS"' not in blk:
            continue
        for a, b in re.findall(r"\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)", blk):
            out.append(B._xform(p, float(a), float(b)))
    return out


def main():
    apply_ = "--apply" in sys.argv
    B = C.Board(C.PCB)
    t = B.t

    # uuid -> (ref, pin), and pad centre, exactly as pin_labels keys them
    owner, padpos = {}, {}
    for p in B.parts:
        m = re.search(r'\(property "Reference" "(J\d+)"', p["blk"])
        if not m:
            continue
        for pd in B.pads(p):
            u = str(uuid.uuid5(P.NS, f"caryatid-pinlabel-{m.group(1)}-{pd['num']}"))
            owner[u] = (m.group(1), pd["num"])
            padpos[(m.group(1), pd["num"])] = (pd["x"], pd["y"])

    found = {}
    for m in re.finditer(r'^\t\(gr_text "([^"]*)"', t, re.M):
        blk = C.sexp(t, m.start() + 1)
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        if not u or u.group(1) not in owner:
            continue
        ref, pin = owner[u.group(1)]
        if ref not in FITS:
            continue
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        sz = re.search(r'\(size ([\d.]+)', blk)
        found.setdefault(ref, []).append({
            "start": m.start(), "blk": blk, "text": m.group(1), "pin": pin,
            "x": float(at.group(1)), "y": float(at.group(2)),
            "rot": float(at.group(3) or 0), "size": float(sz.group(1)), "at": at})

    obst = P.Obstacles(B)          # footprint silk, visible fields, every pad
    CLEAR = 0.26

    edits, skipped = [], []
    for ref in sorted(found, key=lambda r: int(r[1:])):
        L = found[ref]
        p = [q for q in B.parts if q["ref"] == ref][0]
        pts = silk_pts(B, p)
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        # THE AXIS COMES FROM THE PADS, NOT THE TEXT ROTATION. J17 and J18
        # stack their pads vertically and print horizontal text; reading the
        # axis off the rotation laid them out along X instead and pushed `R`
        # to x 196.0, next to the board edge. Caught on a copy.
        pp = [padpos[(ref, l["pin"])] for l in L]
        vert = (max(q[1] for q in pp) - min(q[1] for q in pp)) > \
               (max(q[0] for q in pp) - min(q[0] for q in pp))
        lo, hi = (min(ys), max(ys)) if vert else (min(xs), max(xs))
        up, dn = P.th_split(L[0]["size"])
        h = up + dn
        # baseline: the existing cross-axis column nearest the connector
        cross = [l["x"] if vert else l["y"] for l in L]
        base = min(cross, key=lambda v: abs(v - (p["x"] if vert else p["y"])))
        # order along the axis by the PAD, so the ends are the true ends
        L.sort(key=lambda l: padpos[(ref, l["pin"])][1 if vert else 0])
        mine = []
        for i, l in enumerate(L):
            # extent ALONG THE AXIS: the text's width if it runs that way,
            # otherwise its height
            along = (round(l["rot"]) % 180 == 90) == vert
            w = P.tw(l["text"], l["size"]) if along else h
            if i == 0:
                pos = lo + w / 2
            elif i == len(L) - 1:
                pos = hi - w / 2
            else:
                pos = padpos[(ref, l["pin"])][1 if vert else 0]
            nx, ny = (base, pos) if vert else (pos, base)
            mine.append((l, ref, nx, ny, w))
        # VERIFY BEFORE COMMITTING, PER CONNECTOR, ALL OR NOTHING. Justifying
        # to the outline is pure geometry and knows nothing about neighbours;
        # pin_labels' original placement did. Without this, J3's labels landed
        # on C2 and C9 and were clipped by solder mask, and J12 pushed RED into
        # GRN at 0.088 mm. A half-moved connector would look deliberate.
        # Only check labels that MOVE. An unmoved label is already validated by
        # the status quo, and the obstacle model is stricter than DRC -- J17 and
        # J18 keep their middle label on its pad, where it has always sat on the
        # connector's own reference, and checking it rejected both connectors
        # for a condition this change does not create.
        bad = None
        for l, _, nx, ny, w in mine:
            if abs(l["x"] - nx) < 1e-6 and abs(l["y"] - ny) < 1e-6:
                continue
            up2, dn2 = P.th_split(l["size"])
            hw = (w / 2) if ((round(l["rot"]) % 180 == 90) == vert) else (P.tw(l["text"], l["size"]) / 2)
            box = ((nx - hw, ny - up2, nx + hw, ny + dn2) if not vert
                   else (nx - up2, ny - w / 2, nx + dn2, ny + w / 2))
            hit = obst.clash(box, CLEAR)
            if hit:
                bad = f"{l['text']} hits {hit}"
                break
        for a in range(len(mine)):
            for b in range(a + 1, len(mine)):
                la, lb = mine[a], mine[b]
                pa = la[4] / 2 + lb[4] / 2
                d = abs((la[3] - lb[3]) if vert else (la[2] - lb[2]))
                if d - pa < CLEAR:
                    bad = f"{la[0]['text']} and {lb[0]['text']} only {d - pa:.3f} mm apart"
        if bad:
            skipped.append((ref, bad))
            print(f"  {ref:5} SKIPPED -- {bad}")
            continue
        edits.extend([(l, r, nx, ny) for l, r, nx, ny, _ in mine])
        span = hi - lo
        tot = sum(P.tw(l["text"], l["size"]) for l in L)
        print(f"  {ref:5} {len(L)} labels, {'vertical' if vert else 'horizontal'}, "
              f"baseline {base:.3f}, span {span:.2f} vs text {tot:.2f}")
        for l, _, nx, ny in [e for e in edits if e[1] == ref]:
            print(f"        {l['text']:5} ({l['x']:7.3f},{l['y']:7.3f}) -> ({nx:7.3f},{ny:7.3f})")

    moved = sum(1 for l, _, nx, ny in edits
                if abs(l["x"] - nx) > 1e-6 or abs(l["y"] - ny) > 1e-6)
    print(f"\n  {len(edits)} labels moved across {len(found)-len(skipped)} connectors"
          + (f"; {len(skipped)} skipped" if skipped else ""))

    for l, ref, nx, ny in sorted(edits, key=lambda e: -e[0]["start"]):
        blk, at = l["blk"], l["at"]
        new = blk[:at.start()] + f'(at {nx:.3f} {ny:.3f} {l["rot"]:g})' + blk[at.end():]
        if "(locked yes)" not in new:
            head = new.index("\n") + 1
            new = new[:head] + "\t\t(locked yes)\n" + new[head:]
        t = t[:l["start"] + 1] + new + t[l["start"] + 1 + len(blk):]

    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if not apply_:
        print("  dry run -- pass --apply to write")
        return 0
    open(C.PCB, "w").write(t)
    print(f"  wrote {C.PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())