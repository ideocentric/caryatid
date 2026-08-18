#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mark the analysed-and-accepted DRC items as excluded, with their reasons.

    python3 tools/drc_exclusions.py            # GATE: any violation not accepted?
    python3 tools/drc_exclusions.py --apply    # also write KiCad exclusions

WHY BOTHER
----------
Seven warnings that are all known-good is worse than none, because the eighth
one -- the real one -- arrives and looks exactly like the noise. Excluding the
known set makes a clean DRC run mean something again.

kicad-cli honours project exclusions: by default they are dropped from the
report entirely, and `--severity-all` brings them back tagged as excluded. So
after this, `kicad-cli pcb drc` reporting anything at all is news.

THE SAFETY PROPERTY THAT MATTERS
--------------------------------
This tool CANNOT exclude something new. Every exclusion has to match an entry
in ACCEPTED below by (violation type, item descriptions) -- an explicit
allow-list, each with a written reason. A violation that does not match is
reported as NEW and the tool refuses to write anything at all.

That is the whole point. A tool that re-ran DRC and excluded whatever it found
would silently bless the next real defect, which is the opposite of what
exclusions are for.

TWO MECHANISMS, AND WHY
-----------------------
1. THE GATE, which always works. Every violation is matched against ACCEPTED
   below by (type, item descriptions). Anything unmatched is reported as NEW
   and the tool exits nonzero. This is the part that makes a run meaningful,
   and it does not depend on KiCad's file format at all.

2. KiCad-native exclusions, which only partly work. KiCad stores them in the
   .kicad_pro as a pipe-joined string:

       <type>|<x_nm>|<y_nm>|<uuid_a>|<uuid_b>

   with uuid_b all-zeroes for a single-item violation. That is not documented
   and there was no example on disk, so it was established empirically. THREE
   OF THE SEVEN TAKE; the other four do not, with byte-identical structure and
   verified-correct uuids and coordinates. Brute-forcing the variants for one
   of them -- no comment, no trailing uuid, uuid duplicated, zeroed position,
   placed first in the list -- moved nothing. The API stores comments in a
   separate map (m_DrcExclusionComments), so the key almost certainly carries
   something not reproducible from the JSON report.

   So --apply writes them, then RE-RUNS DRC and reports how many actually took.
   It does not claim success it has not measured. That check is the whole
   lesson from the first attempt, which wrote seven and assumed seven.

   To finish the other four: exclude them once in KiCad's DRC panel
   (right-click -> Exclude this violation), save, and the strings KiCad writes
   can be read straight out of the .kicad_pro.

An exclusion stops matching if the item moves or is replaced, which is the
behaviour you want -- MOVE A PART AND ITS EXCLUSION LAPSES. Re-run after any
placement change.
"""
import sys, os, re, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CLI = CLI if os.path.exists(CLI) else "kicad-cli"
PRO = os.path.splitext(C.PCB)[0] + ".kicad_pro"
NULL = "00000000-0000-0000-0000-000000000000"

# (type, item descriptions) -> why it is accepted. Nothing outside this table
# can be excluded. Keep the reasons short enough to read in KiCad's DRC panel.
ACCEPTED = {
    ("lib_footprint_mismatch", ("Footprint C4",)):
        "pad angle differs from library by exactly 180 deg; a rectangle is "
        "symmetric under it. C4 and C5 have identical pad geometry in pcbnew "
        "and only C4 is flagged. Gerbers come from the board, not the library.",
    ("lib_footprint_mismatch", ("Footprint C6",)):
        "pad angle 180 deg from library; same rectangle. Resolves to "
        "1.450 x 1.000 mm for its -90 deg placement, which is correct.",
    ("lib_footprint_mismatch", ("Footprint L1",)):
        "pad angle 180 deg from library; same rectangle. Resolves to "
        "1.150 x 3.600 mm, which is correct.",
    ("lib_footprint_mismatch", ("Footprint A1",)):
        "metadata only -- pads and graphics are byte-identical to the library.",
    ("lib_footprint_mismatch", ("Footprint A2",)):
        "metadata only -- pads and graphics are byte-identical to the library.",
    ("silk_overlap", ("Reference field of J11", "Segment of J11 on F.Silkscreen")):
        "0.2098 mm silk-to-silk. Our rule is 0.25, a legibility preference; "
        "JLC's floor is 0.15. Not over copper.",
    ("silk_overlap", ("Segment of BT1 on F.Silkscreen", "Footprint text of BT1 (+)")):
        "0.2121 mm silk-to-silk between BT1's outline and its + marker. Our "
        "rule is 0.25; JLC's floor is 0.15. Not over copper. Worth an eye on "
        "the fab preview since it is a polarity marker.",
}


def run_drc():
    out = "/tmp/drc-exclusions.json"
    r = subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all",
                        "-o", out, C.PCB], capture_output=True, timeout=900)
    if not os.path.exists(out):
        print("  DRC produced no output:", r.stderr.decode()[:200]); sys.exit(1)
    d = json.load(open(out)); os.remove(out)
    return d.get("violations", [])


def run_drc_plain():
    """DRC as it reports day to day -- exclusions already dropped."""
    out = "/tmp/drc-exclusions-plain.json"
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", out, C.PCB],
                   capture_output=True, timeout=900)
    if not os.path.exists(out): return []
    d = json.load(open(out)); os.remove(out)
    return d.get("violations", [])


def key(v):
    return (v["type"], tuple(i["description"] for i in v["items"]))


def serialise(v, reason):
    it = v["items"]
    a = it[0]["uuid"]
    b = it[1]["uuid"] if len(it) > 1 else NULL
    p = it[0]["pos"]
    return f'{v["type"]}|{round(p["x"]*1e6)}|{round(p["y"]*1e6)}|{a}|{b}|{reason}'


def main():
    apply_ = "--apply" in sys.argv
    viols = run_drc()
    matched, new = [], []
    for v in viols:
        k = key(v)
        (matched if k in ACCEPTED else new).append(v)

    print(f"  {len(viols)} violations with --severity-all\n")
    for v in matched:
        print(f"  accepted  {v['type']:<24} {', '.join(i['description'] for i in v['items'])}")
    for v in new:
        print(f"  NEW       {v['type']:<24} {', '.join(i['description'] for i in v['items'])}")
        print(f"            {v['description']}")

    unused = [k for k in ACCEPTED if k not in {key(v) for v in viols}]
    for k in unused:
        print(f"  stale     {k[0]:<24} {', '.join(k[1])}  (no longer reported)")

    if new:
        print(f"\n  REFUSING: {len(new)} violation(s) are not in the accepted table.")
        print("  Decide on them, add them to ACCEPTED with a reason, then re-run.")
        return 1

    print(f"\n  GATE: {len(new)} new, {len(matched)} accepted -- clean")
    if not apply_:
        print("  pass --apply to also write KiCad exclusions")
        return 0

    lines = [serialise(v, ACCEPTED[key(v)]) for v in matched]
    pro = json.load(open(PRO))
    pro.setdefault("board", {}).setdefault("design_settings", {})["drc_exclusions"] = lines
    json.dump(pro, open(PRO, "w"), indent=2)

    # Measure, do not assume. The first version of this wrote seven and
    # reported seven; three took.
    after = [v for v in run_drc_plain()]
    took = len(matched) - len(after)
    print(f"  wrote {len(lines)} exclusions; {took} of {len(lines)} took effect")
    if after:
        print(f"  {len(after)} still report in a plain DRC run -- KiCad did not "
              f"accept those keys:")
        for v in after:
            print(f"    {v['type']:<24} {', '.join(i['description'] for i in v['items'])}")
        print("  Exclude these once in KiCad's DRC panel and re-read the format.")
    return 0


if __name__ == "__main__":
    sys.exit(main())