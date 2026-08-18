#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check every LCSC code in lcsc.yaml against what JLC actually stocks.

    python3 tools/verify_parts.py
    python3 tools/verify_parts.py --json local/fab/parts.json

Fetches each part from JLC's cart API and compares the returned description
against what the design needs -- value, package, voltage rating, tolerance,
dielectric. Reports library type, stock and price alongside, because those are
the two things a correct part can still be wrong about.

WHY THIS EXISTS
---------------
Part numbers were chosen by searching a catalogue and reading a results table.
That is exactly the step where a 16 V part becomes a 6.3 V part, or an 0805
becomes an 0603, without anything downstream noticing: the BOM is just a
string, the Gerbers do not care, and DRC cannot see it. The first assembled
board is otherwise where you find out.

WHAT IT CANNOT DO
-----------------
It compares text. A part whose description omits a rating is reported as
UNKNOWN rather than passed, and the constraints that no description carries --
C6's effective capacitance under bias, C7 needing real ESR -- are printed as
reminders because no field in this API expresses them.
"""
import sys, os, re, json, time, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

API = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode="
MAP = os.path.join(os.path.dirname(C.PCB), "lcsc.yaml")

# what the design needs, keyed by the value string used in the BOM
NEED = {
    "1k":       dict(pkg="0603", res="1kΩ"),
    "100R":     dict(pkg="0603", res="100Ω"),
    "100k":     dict(pkg="0603", res="100kΩ"),
    "300":      dict(pkg="0603", res="300Ω"),
    "1k2":      dict(pkg="0603", res="1.2kΩ"),
    "887R 1%":  dict(pkg="0603", res="887Ω",  tol="±1%"),
    "46k4":     dict(pkg="0603", res="46.4kΩ", tol="±1%"),
    "0R":       dict(pkg="0603", res="0Ω"),
    "348k 1%":  dict(pkg="0603", res="348kΩ", tol="±1%"),
    "47k5 1%":  dict(pkg="0603", res="47.5kΩ", tol="±1%"),
    "510":      dict(pkg="0603", res="510Ω"),
    "10k":      dict(pkg="0603", res="10kΩ"),
    "10k 0.1%": dict(pkg="0603", res="10kΩ", tol="±0.1%"),
    "100n":     dict(pkg="0603", cap="100nF", vmin=16),
    "10n":      dict(pkg="0603", cap="10nF",  vmin=16),
    "220n":     dict(pkg="0603", cap="220nF", vmin=16),
    "1u":       dict(pkg="0603", cap="1uF",   vmin=16),
    "10u":      dict(pkg="0805", cap="10uF",  vmin=16),
    "10u/25V":  dict(pkg="0805", cap="10uF",  vmin=25),
    "22u":      dict(pkg="0805", cap="22uF",  vmin=16),
    "100u":     dict(cap="100uF", vmin=10),
}
REMINDER = {
    "C6":  "needs >=4 uF EFFECTIVE at 5 V bias (SLVSF14B 8.2.2.3) -- check the "
           "part's own DC-bias curve, no catalogue field states it",
    "C7":  "must be an ALUMINIUM ELECTROLYTIC; its ESR damps the FB1/C7 filter",
    "FB1": "DCR <=50 mohm and >=1 A; it carries the whole 5 V rail",
    "R3":  "1% is a datasheet requirement -- the bq24074 short-tests RISET",
}


def fetch(code):
    """Via curl. urllib fails certificate verification on this machine where
    curl succeeds, and a fetch that silently returns nothing would read as a
    clean result."""
    r = subprocess.run(["curl", "-sS", "--max-time", "20", "-A", "Mozilla/5.0",
                        API + code], capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(r.stderr.strip()[:80] or "empty response")
    return json.loads(r.stdout).get("data") or {}


def codes():
    """Keys and codes may sit on one line or two -- by_value_footprint entries
    wrap. Reading only single-line entries found 8 of 29."""
    out, pending = {}, None
    for line in open(MAP):
        s = line.strip()
        if not s or s.startswith("#"): continue
        m = re.search(r'^"?([^":]+?)"?:\s*\{lcsc:\s*(C\d+)', s)
        if m:
            out.setdefault(m.group(2), []).append(m.group(1)); pending = None; continue
        m = re.search(r'^"?([^":]+?)"?:\s*$', s)
        if m: pending = m.group(1); continue
        m = re.search(r'^\{lcsc:\s*(C\d+)', s)
        if m and pending:
            out.setdefault(m.group(1), []).append(pending); pending = None
    return out


def main():
    want = codes()
    print(f"  {len(want)} distinct LCSC codes in lcsc.yaml\n")
    results, bad = {}, []
    for i, (code, keys) in enumerate(sorted(want.items())):
        try:
            d = fetch(code)
        except Exception as e:
            print(f"  {code:<11} FETCH FAILED: {e}"); continue
        results[code] = d
        desc = (d.get("describe") or "").strip()
        lib = {"base": "Basic", "expand": "Extended"}.get(d.get("componentLibraryType"),
                                                          d.get("componentLibraryType"))
        stock = d.get("stockCount", 0)
        key = keys[0].split("|")[0]
        need = NEED.get(key, {})
        probs = []
        low = desc.lower()
        if need.get("pkg") and need["pkg"] not in desc: probs.append(f"package != {need['pkg']}")
        if need.get("res"):
            r = need["res"].replace("Ω", "").lower()
            if r not in low.replace("ω", "").replace(" ", ""): probs.append(f"value != {need['res']}")
        if need.get("cap"):
            c = need["cap"].lower().replace("u", "μ")
            if c not in low and need["cap"].lower() not in low: probs.append(f"value != {need['cap']}")
        if need.get("tol") and need["tol"] not in desc and need["tol"].replace("±","") not in desc:
            probs.append(f"tolerance != {need['tol']}")
        if need.get("vmin"):
            vs = re.findall(r"(\d+(?:\.\d+)?)\s*V\b", desc)
            v = max((float(x) for x in vs), default=None)
            if v is None: probs.append("no voltage rating in the description")
            elif v < need["vmin"]: probs.append(f"voltage {v:g}V < {need['vmin']}V required")
        flag = "  <-- " + "; ".join(probs) if probs else ""
        if probs: bad.append((code, keys, desc, probs))
        print(f"  {code:<11} {lib or '?':<9} stock {stock:>7}  {desc[:64]}{flag}")
        print(f"              {', '.join(k[:44] for k in keys)}")
        time.sleep(0.35)
    print(f"\n  {len(bad)} of {len(results)} flagged")
    print("\n  constraints no catalogue field can express:")
    for k, v in REMINDER.items():
        print(f"    {k:<5} {v}")
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(results, open(p, "w"), indent=1)
        print(f"\n  raw data -> {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())