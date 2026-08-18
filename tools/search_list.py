#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the JLCPCB search worklist for parts that still have no LCSC code.

    .venv/bin/python tools/search_list.py            # print
    .venv/bin/python tools/search_list.py --apply    # write local/fab/search.csv

Driven by the same gap `fab_package.py` reports, so it cannot drift: a part that
gains a code in hardware/pcb/lcsc.yaml drops off this list automatically.

The SPEC column is what to filter on in JLC's parametric search. It is derived
in docs/sourcing.md -- rail-by-rail for the capacitors, from dissipation for the
resistors -- rather than copied off the value. Two entries carry constraints
that a search filter will not enforce and that quietly matter:

  C6  is the boost's OUTPUT capacitor and needs >=4 uF EFFECTIVE at 5 V bias,
      not 22 uF nominal. SLVSF14B 8.2.2.3: below that range the regulator "can
      potentially become unstable", and a ceramic "can lose more than 50% of
      its capacitance at its rated voltage".

  C7  must be an ALUMINIUM ELECTROLYTIC. Its ESR is the only damping on the
      FB1/C7 filter. A ceramic of the same value takes Q from 0.12 to about 20
      and puts roughly 26 dB of peaking near 16 kHz on the rail feeding the
      codec.
"""
import sys, os, csv, subprocess, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(C.PCB))),
                   "local", "fab", "search.csv")

# value -> (spec to filter on, constraint a filter will not catch, search term)
SPEC = {
    # A -- 0603 resistors. 1%, 100 mW. Worst placed dissipation is 17.6 mW.
    "R": ("0603, 1%, 100 mW, thick film", "", "resistor 0603 1% {v}"),
    # B -- 0603 MLCC, everything on rails at 3.3 V or below
    "C0603": ("0603, X7R, >=16 V, +/-10%", "", "capacitor 0603 X7R {v} 16V"),
    # C -- 0805 MLCC
    "C0805": ("0805, X5R/X7R, >=16 V", "", "capacitor 0805 X7R {v} 16V"),
}
OVERRIDE = {
    "C1":  ("0805, X5R/X7R, **25 V**", "raw barrel input, up to 9 V, OVP to 28 V",
            "capacitor 0805 X7R 10uF 25V"),
    "C6":  ("0805, X5R/X7R, >=16 V", "BOOST OUTPUT CAP: needs >=4 uF EFFECTIVE at "
            "5 V bias (SLVSF14B 8.2.2.3). Check the part's DC-bias curve.",
            "capacitor 0805 X7R 22uF 16V"),
    "C7":  ("CP_Elec_6.3x5.4, 100 uF, >=10 V (16 V better), 105 C",
            "ALUMINIUM ELECTROLYTIC, NOT ceramic. Its ESR damps the FB1/C7 "
            "filter; a ceramic gives ~26 dB peaking near 16 kHz.",
            "aluminium electrolytic 100uF 16V SMD 6.3x5.4"),
    "FB1": ("0805 ferrite bead, >=1 A, DCR <=50 mohm, 120-600 ohm @100 MHz",
            "carries the whole 5 V rail; 50 mohm = 30 mV drop at 600 mA",
            "ferrite bead 0805 1A 600ohm"),
    "J16": ("2x4 pin header, 2.54 mm, vertical THT", "", "pin header 2x4 2.54mm"),
    "R3":  ("0603, **1%**, 100 mW", "datasheet requirement -- the bq24074 "
            "short-tests RISET at maximum charge setting", "resistor 0603 1% 887R"),
    "R7":  ("0603, **1%**, 100 mW", "sets the boost output voltage; 109 mV to OVP",
            "resistor 0603 1% 348k"),
    "R8":  ("0603, **1%**, 100 mW", "sets the boost output voltage; 109 mV to OVP",
            "resistor 0603 1% 47k5"),
    "R4":  ("0603, 1%, 100 mW", "E96 value -- check it is Basic, not Extended",
            "resistor 0603 1% 46k4"),
}


def main():
    apply_ = "--apply" in sys.argv
    subprocess.run([sys.executable, os.path.join(HERE, "fab_package.py")],
                   capture_output=True, timeout=900)
    rows = list(csv.DictReader(open("/tmp/caryatid-fab/bom.csv")))
    out = []
    for r in rows:
        if r.get("LCSC"): continue
        refs, val = r["Reference"], r["Value"]
        fp = r["Footprint"].split(":")[-1]
        first = re.split(r"[,\-]", refs)[0].strip()
        if first in OVERRIDE:
            spec, note, term = OVERRIDE[first]
        elif fp.startswith("R_0603"):
            spec, note, term = SPEC["R"]
        elif fp.startswith("C_0603"):
            spec, note, term = SPEC["C0603"]
        elif fp.startswith("C_0805"):
            spec, note, term = SPEC["C0805"]
        else:
            spec, note, term = ("see docs/sourcing.md", "", val)
        grp = ("A resistors 0603" if fp.startswith("R_0603") else
               "B MLCC 0603" if fp.startswith("C_0603") else
               "C MLCC 0805" if fp.startswith("C_0805") else
               "D electrolytic" if fp.startswith("CP_") else
               "E ferrite" if fp.startswith("L_") else "F connector")
        out.append({
            "Set": grp, "Designators": refs, "Qty": r["QUANTITY"], "Value": val,
            "Package": fp, "Spec to filter on": spec,
            "Constraint a filter will NOT catch": note,
            "Suggested JLC search": term.replace("{v}", val),
            "LCSC": "", "Basic or Extended": "", "Unit price": "", "Notes": "",
        })
    out.sort(key=lambda x: (x["Set"], -int(x["Qty"])))
    w = csv.DictWriter(sys.stdout, fieldnames=list(out[0].keys()))
    tot = sum(int(x["Qty"]) for x in out)
    print(f"  {len(out)} lines, {tot} parts to source\n")
    for grp in sorted({x["Set"] for x in out}):
        n = sum(int(x["Qty"]) for x in out if x["Set"] == grp)
        print(f"    {grp:<20} {sum(1 for x in out if x['Set']==grp):>2} lines, {n:>2} parts")
    if apply_:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", newline="") as f:
            w2 = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w2.writeheader(); w2.writerows(out)
        print(f"\n  wrote {OUT}")
    else:
        print("\n  pass --apply to write the csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())