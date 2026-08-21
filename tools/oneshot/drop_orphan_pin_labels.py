#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Delete ten pin labels that a rename orphaned, and a lock then made permanent.

    python3 tools/oneshot/drop_orphan_pin_labels.py --apply

HOW TEN LABELS BECAME UNREACHABLE
----------------------------------
`pin_labels.py` derives each label's uuid from its connector's name:

    uuid5(NS, f"caryatid-pinlabel-{ref}-{pin}")

`276149a` then renamed **J13A -> J13** and **J13B -> J19**, because KiCad would
not accept the old names. The labels already on the board kept the uuids
computed from the OLD names, so from that moment the tool did not own them: not
in KNOWN, therefore never stripped, never regenerated, never moved.

`faea30a` then locked every label on the board to stop re-runs reverting hand
nudges. That sealed it. Ten labels that nothing owned were now also protected
from removal, and `--relock` -- the escape hatch -- only forces the strip of
labels the tool KNOWS about. These were invisible to it in both directions.

**They were not duplicates until today.** They were the only labels J13 and J19
had, which is why nothing looked wrong: the board rendered correctly and the
count came out right. Regenerating against the new placement produced the real
ones, and only then did the orphans become a second set at stale coordinates --
J19 carrying 11 labels where six pins exist, and J13's four stranded 6 mm from
where J13 now sits.

WHY BY EXPLICIT UUID
--------------------
The general rule -- "locked, looks like a pin label, unowned" -- would also
match any hand-placed text someone deliberately locked. These ten are named
individually so this can only ever remove these ten.

WHAT SHOULD FOLLOW. Two things are worth fixing properly, and neither belongs
in a one-shot:

  * a rename should re-key the labels, or the uuid should not encode the
    reference at all
  * `pin_labels.py` should REPORT locked labels it does not own, rather than
    silently skipping them. Nothing said these existed for six commits.
"""
import sys, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_board as C

PCB = os.path.join(ROOT, "hardware", "pcb", "caryatid.kicad_pcb")

# uuid, and what it reads, from the board before removal
ORPHANS = [
    ("1e8795cd-e715-5d31-bb3e-a38aecc3a761", "D11", "J19 under its old name J13B"),
    ("34b912b1-127e-5a51-8270-4544e4a76dbb", "5V",  "J19 under its old name J13B"),
    ("3526ca78-f2db-53fd-a400-9bb7ae6aed9b", "3V3", "J19 under its old name J13B"),
    ("50b5b174-a2bb-5974-95a5-ed85b9252746", "GND", "J19 under its old name J13B"),
    ("60df294d-9b3e-5b7f-8c26-6f7c64edb32a", "GND", "J19 under its old name J13B"),
    ("a7a044be-1f3b-505f-8c15-ef712a4bd5cc", "D12", "J19 under its old name J13B"),
    ("63733644-f5b5-53b5-84c7-2d44c44be30d", "GND", "J13 under its old name J13A"),
    ("9019d0a2-347e-5980-b285-c4930145a3f4", "3V3", "J13 under its old name J13A"),
    ("bad673e4-91f2-5417-8977-ad8f56fc003e", "D12", "J13 under its old name J13A"),
    ("cd7d5713-6085-5c03-973c-f58ac8a5e066", "D11", "J13 under its old name J13A"),
]


def main():
    t = open(PCB).read()
    want = {u: (txt, why) for u, txt, why in ORPHANS}
    removed = []
    while True:
        hit = None
        for m in re.finditer(r"^\t\(gr_text\b", t, re.M):
            blk = C.sexp(t, m.start() + 1)
            u = re.search(r'\(uuid "([^"]+)"\)', blk)
            if not (u and u.group(1) in want):
                continue
            txt = re.match(r'\(gr_text "([^"]*)"', blk).group(1)
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
            if txt != want[u.group(1)][0]:
                sys.exit(f"  {u.group(1)} reads '{txt}', expected "
                         f"'{want[u.group(1)][0]}'. Not writing.")
            e = m.start() + 1 + len(blk)
            while e < len(t) and t[e] == "\n":
                e += 1
            hit = (m.start(), e, u.group(1), txt, at.group(1), at.group(2))
            break
        if not hit:
            break
        t = t[:hit[0]] + t[hit[1]:]
        removed.append(hit[2:])
        print(f'    - "{hit[3]}" at ({hit[4]}, {hit[5]})  {want[hit[2]][1]}')

    missing = set(want) - {r[0] for r in removed}
    if missing:
        sys.exit(f"  {len(missing)} not found: {sorted(missing)}. "
                 f"Already applied, or the board changed. Not writing.")
    print(f"  removed {len(removed)} orphaned labels")

    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(PCB, "w").write(t)
    print(f"  wrote {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())