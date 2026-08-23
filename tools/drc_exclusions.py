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

2. KiCad-native exclusions. THIS TOOL NEVER INVENTS ONE. Excluding is done in
   KiCad's DRC panel (right-click -> Exclude this violation); the tool reads
   what KiCad wrote, attaches the documented reason to it, and prunes entries
   that no longer match a reported violation.

   That division of labour is not fastidiousness, it is the result of trying
   the other way. KiCad stores each entry as a two-element array:

       ["<type>|<x_nm>|<y_nm>|<uuid_a>|<uuid_b>", "<comment>"]

   An earlier version of this tool synthesised that key from the JSON DRC
   report. THREE OF SEVEN TOOK. The uuids and the type were right every time;
   the COORDINATE was not. For C4, C6 and L1 the key position is the footprint
   anchor and the guess happened to be correct. For A1 and A2 it is neither the
   anchor nor the bounding-box centre -- both carry an identical x of
   118.6825 mm that corresponds to no obvious feature -- and for silk_overlap
   it is neither item's reported position. It is not reconstructible from
   anything the report exposes, so it is not synthesised.

   Matching an exclusion to its violation uses (type, uuid_a, uuid_b), which
   IS reconstructible and is stable across moves. The coordinate is carried
   through verbatim and never recomputed.

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
#
# Entries come OUT when the item is fixed rather than accepted. Both
# silk_overlap entries were here and both are gone -- J11's reference nudged
# clear, BT1's + marker moved from local x -4.5 to -5.5. Nothing on this board
# is accepted that could have been fixed instead. The tool reports a
# table entry that no longer matches anything as "stale", so this list cannot
# quietly accumulate permissions for things that stopped happening.
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
    # R45 WAS HERE AND WAS FIXED INSTEAD OF EXCLUDED, 2026-08-22. Its pads were
    # stored at 270 deg against a footprint at 90 -- 180 RELATIVE, where
    # Resistor_SMD has 0 -- and it was the ONLY one of 64 0603 resistors on the
    # board like that; the other 28 at 90 deg all store 90. The half turn was
    # harmless (a 0.800 x 0.950 rectangle is unchanged by it, and both pad
    # centres are identical before and after), which is exactly why excusing it
    # was the wrong call: a lone outlier that costs nothing to normalise should
    # be normalised, not written into the allow-list. It picked up the flip when
    # 3fe330e rotated it beside J9/J10.
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


def uuid_key(v):
    """(type, uuid_a, uuid_b) -- the part of an exclusion that is stable and
    reconstructible. The coordinate is not, so it is never recomputed."""
    it = v["items"]
    return (v["type"], it[0]["uuid"], it[1]["uuid"] if len(it) > 1 else NULL)


def parse_entry(e):
    """KiCad writes ["<key>", "<comment>"]. Older files, and an earlier version
    of this tool, hold a bare string."""
    if isinstance(e, list):
        return e[0], (e[1] if len(e) > 1 else "")
    return e, ""


def entry_uuid_key(keystr):
    f = keystr.split("|")
    return (f[0], f[3], f[4]) if len(f) >= 5 else None


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

    pro = json.load(open(PRO))
    ds = pro.setdefault("board", {}).setdefault("design_settings", {})
    existing = [parse_entry(e) for e in ds.get("drc_exclusions", [])]
    live = {uuid_key(v): v for v in viols}

    out, annotated, pruned = [], 0, []
    for keystr, comment in existing:
        uk = entry_uuid_key(keystr)
        if uk not in live:
            pruned.append(keystr.split("|")[0]); continue
        reason = ACCEPTED.get(key(live[uk]), comment)
        annotated += reason != comment
        out.append([keystr, reason])
    ds["drc_exclusions"] = out
    json.dump(pro, open(PRO, "w"), indent=2)

    print(f"  {len(out)} exclusions kept, {annotated} given their documented reason"
          + (f", {len(pruned)} pruned as stale ({', '.join(pruned)})" if pruned else ""))

    # Measure, do not assume.
    after = run_drc_plain()
    print(f"  plain DRC now reports {len(after)} violation(s)")
    missing = [v for v in matched if uuid_key(v) not in
               {entry_uuid_key(k) for k, _ in [parse_entry(e) for e in out]}]
    for v in missing:
        print(f"  NOT EXCLUDED  {v['type']:<22} "
              f"{', '.join(i['description'] for i in v['items'])}")
    if missing:
        print("  -> exclude these in KiCad's DRC panel; this tool will not invent a key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())