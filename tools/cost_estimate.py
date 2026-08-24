#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Estimate what a build costs, and show which lines are guesses.

    .venv/bin/python tools/cost_estimate.py              # 5 and 10
    .venv/bin/python tools/cost_estimate.py 5 10 25
    .venv/bin/python tools/cost_estimate.py --quote 169  # reconcile a real quote

WHY THIS IS A TOOL AND NOT A TABLE IN A DOC
-------------------------------------------
Every input here moves. Part prices change, stock changes, the BOM changes, and
a table transcribed into a document is wrong within a week while still reading
like a fact. This pulls the price ladders live and counts the joints off the
board, so the only things it cannot check are JLC's service rates -- which are
isolated in RATES below, in one block, clearly labelled.

WHAT IS EXACT AND WHAT IS NOT
-----------------------------
EXACT: the parts line. Fetched per code from JLC's cart API, with the correct
price band selected for the actual order quantity, MOQ respected, and the BT1
pre-order price substituted for the public ladder -- the public endpoint does
not see the pre-order route and quotes $5.0468 against the real $4.8616.

MEASURED: joint counts and the Extended/Basic split, read off the board and the
API rather than assumed. assemblyModeBatch separates the SMT line from the
hand-soldered through-hole parts; on this board those are two different rates
and 111 of the 211 joints are the expensive kind.

GUESSED: everything in RATES, and the PCB fab line most of all. 150 x 90 mm is
past JLC's 100 x 100 cheap tier so it is area-priced, and this does not model
their area formula -- PCB_FAB is a flat guess per quantity. PCB_FAB[5] is now
MEASURED from a real order; every other quantity is still a placeholder.

WHAT THIS TOOL DOES NOT COST AT ALL, AND IT IS THE LARGEST LINE
---------------------------------------------------------------
MERCHANDISE ONLY. Shipping, customs duties, payment fees and sales tax are not
modelled and are not small: on the 2026-08-23 order of five they added $130.71
to $176.24 of goods, a 74% uplift, with duties alone at 36% of merchandise.
An estimate that lands within 9% of the goods total can still be half the money
that actually leaves the account. Reconcile against MERCHANDISE, and treat the
landed figure as a separate number that only a real order can give you.

THE POINT THE ESTIMATE IS ACTUALLY MAKING
-----------------------------------------
Fixed cost dominates at these quantities. The setup fee plus the per-unique-part
Extended loading fee do not scale with the build, so doubling the boards is
nowhere near doubling the bill. The fee is per UNIQUE PART, not per BOM line --
getting that wrong understates it by about half, which is a mistake made once
already in this project.

Use --quote to reconcile: it prints what the real total implies about the lines
this tool had to guess, rather than pretending the estimate was right.
"""
import sys, os, re, csv, json, time, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

API = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode="
BOM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(C.PCB))),
                   "..", "local", "fab", "bom.csv")
BOM = os.path.normpath(BOM)

# ---- GUESSES. Everything uncertain lives here. Correct against a real quote. --
RATES = {
    "setup_fee":        8.00,    # one-time, per order
    "extended_fee":     3.00,    # per UNIQUE Extended part, one-time
    "smt_per_joint":    0.0017,
    "tht_per_joint":    0.0173,  # hand soldering, the expensive one
}
# 5 is MEASURED as of 2026-08-23, the rest are still guesses. A real order of
# five came to $176.24 of merchandise against a $161.68 estimate; attributing
# the whole $14.56 gap to this line, which was the only one flagged as a guess,
# puts fab at $42.56 WITH THE ENIG UPGRADE INCLUDED. That hangs together: the
# $28.00 guess predated the finish change, ENIG cost about $20, so a naive
# expectation was $48 and the real base fab came in cheaper than guessed.
PCB_FAB = {5: 42.56, 10: 40.00, 20: 60.00, 25: 70.00, 50: 120.00}
PCB_FAB_DEFAULT_PER_BOARD = 3.00   # crude fallback for quantities not listed

# The public ladder cannot see pre-order pricing. Confirmed 2026-08-18.
PREORDER_UNIT = {"C5339083": 4.8616}


def fetch(code):
    r = subprocess.run(["curl", "-sS", "--max-time", "20", "-A", "Mozilla/5.0",
                        API + code], capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout).get("data") or {}


def load():
    if not os.path.exists(BOM):
        sys.exit(f"  no {BOM} -- run tools/fab_package.py --apply first")
    codes = collections.OrderedDict()
    for r in csv.DictReader(open(BOM)):
        # The BOM follows JLC's template now: "JLCPCB Part #" and "Designator",
        # with no quantity column -- the count is the number of designators.
        code = (r.get("JLCPCB Part #") or r.get("LCSC") or "").strip()
        if not code: continue
        refs = [x.strip() for x in r["Designator"].split(",") if x.strip()]
        e = codes.setdefault(code, {"n": 0, "refs": []})
        e["n"] += len(refs)
        e["refs"] += refs
    return codes


def unit_price(d, code, order):
    if code in PREORDER_UNIT: return PREORDER_UNIT[code]
    for p in (d.get("prices") or []):
        s, e = p.get("startNumber") or 0, p.get("endNumber")
        if order >= s and (e in (None, -1) or order <= e):
            return p.get("productPrice") or 0.0
    return 0.0


def fab(n):
    return PCB_FAB.get(n, n * PCB_FAB_DEFAULT_PER_BOARD)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quote = None
    if "--quote" in sys.argv:
        quote = float(sys.argv[sys.argv.index("--quote") + 1])
        args = [a for a in args if a != str(quote) and float(a) != quote]
    qtys = [int(a) for a in args] or [5, 10]

    codes = load()
    print(f"  {len(codes)} codes, fetching live prices ...")
    info = {}
    for c in codes:
        info[c] = fetch(c); time.sleep(0.22)

    manual = {c for c in codes if info[c].get("assemblyModeBatch") == "manualWeld"}
    ext = [c for c in codes if info[c].get("componentLibraryType") != "base"]

    B = C.Board(C.PCB)
    pads = {}
    for p in B.parts:
        m = re.search(r'"Reference" "([^"]+)"', p["blk"])
        if m: pads[m.group(1)] = len(re.findall(r'\(pad "', p["blk"]))
    smt_j = sum(pads.get(r, 0) for c, v in codes.items() if c not in manual for r in v["refs"])
    tht_j = sum(pads.get(r, 0) for c, v in codes.items() if c in manual for r in v["refs"])

    print(f"  measured: {smt_j} SMT + {tht_j} THT joints per board, "
          f"{len(ext)} Extended / {len(codes)-len(ext)} Basic, "
          f"{len(manual)} hand-soldered codes\n")

    fixed = RATES["setup_fee"] + len(ext) * RATES["extended_fee"]
    lines, totals = [], {}
    for n in qtys:
        parts = 0.0
        for c, v in codes.items():
            order = max(v["n"] * n, info[c].get("leastNumber", 1) or 1)
            parts += unit_price(info[c], c, order) * order
        row = {
            "PCB fab (GUESS)":            fab(n),
            "setup fee":                  RATES["setup_fee"],
            f"Extended loading x{len(ext)}": len(ext) * RATES["extended_fee"],
            "SMT placement":              smt_j * n * RATES["smt_per_joint"],
            "THT hand solder":            tht_j * n * RATES["tht_per_joint"],
            "parts (EXACT)":              parts,
        }
        totals[n] = sum(row.values()); lines.append((n, row))

    keys = list(lines[0][1].keys())
    w = max(len(k) for k in keys) + 2
    print("  " + " " * w + "".join(f"{n:>12}" for n, _ in lines))
    for k in keys:
        print(f"  {k:<{w}}" + "".join(f"{'$%.2f' % r[k]:>12}" for _, r in lines))
    print("  " + "-" * (w + 12 * len(lines)))
    print(f"  {'TOTAL':<{w}}" + "".join(f"{'$%.2f' % totals[n]:>12}" for n, _ in lines))
    print(f"  {'per board':<{w}}" + "".join(f"{'$%.2f' % (totals[n]/n):>12}" for n, _ in lines))

    print(f"\n  fixed regardless of quantity: ${fixed:.2f}"
          + "".join(f"   {fixed/totals[n]*100:.0f}% of {n}" for n, _ in lines))
    if len(lines) > 1:
        (a, _), (b, _) = lines[0], lines[1]
        d = totals[b] - totals[a]
        print(f"  going {a} -> {b}: +${d:.2f} for {b-a} more boards "
              f"= ${d/(b-a):.2f}/board, against ${totals[a]/a:.2f} for the first {a}")

    if quote is not None:
        n = qtys[0]
        diff = quote - totals[n]
        print(f"\n  RECONCILING a real quote of ${quote:.2f} for {n} boards:")
        print(f"    estimate ${totals[n]:.2f}, out by ${diff:+.2f} ({diff/totals[n]*100:+.0f}%)")
        print(f"    the exact line is parts; the difference lives in the guessed ones.")
        print(f"    if it is all PCB fab, the real fab cost is ${fab(n)+diff:.2f} "
              f"(guessed ${fab(n):.2f}) -- update PCB_FAB[{n}].")
        per_ext = (len(ext)*RATES['extended_fee'] + diff) / len(ext)
        print(f"    if it is all loading fees, the real rate is ${per_ext:.2f} "
              f"per Extended part (guessed ${RATES['extended_fee']:.2f}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
