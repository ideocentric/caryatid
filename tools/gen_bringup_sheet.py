#!/usr/bin/env python3
"""Generate a dated, blank bring-up tally sheet from docs/bringup.md.

WHY THIS EXISTS. The runbook is the reference and is never filled in; readings
go on a dated sheet. Those two used to be written separately and drifted apart
every time the runbook changed, which is exactly the failure the ledger
methodology exists to prevent: a derived document that stops matching its
source. So the sheet is DERIVED. Edit docs/bringup.md, regenerate.

WHAT IT PARSES, and the conventions the runbook must keep:

    # Phase B: Dead board          a phase heading
    > **Scope:** all five boards   the scope line, which decides the columns
    ## B2. Rail to ground          a section heading
    | B2.1 | do this | expect that |   a step row, ANY table whose first cell
                                       is a step id of the form <Phase><n>.<n>

Anything else in the runbook is prose and is ignored. That is deliberate: the
sheet carries what gets recorded, not what gets read.

Usage:
    python3 tools/gen_bringup_sheet.py                 all phases, today
    python3 tools/gen_bringup_sheet.py --phase B       one phase
    python3 tools/gen_bringup_sheet.py --phase B C     several
    python3 tools/gen_bringup_sheet.py --date 2026-09-07 --stdout
"""
import argparse
import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNBOOK = ROOT / "docs" / "bringup.md"
OUTDIR = ROOT / "discovery" / "evidence"

RE_PHASE = re.compile(r"^# Phase ([A-G]): (.+?)\s*$")
RE_SCOPE = re.compile(r"^> \*\*Scope:\*\*\s*(.+?)\s*$")
RE_SECTION = re.compile(r"^## ([A-G]\d+)\.\s*(.+?)\s*$")
RE_STEP = re.compile(r"^\|\s*([A-G]\d+\.\d+)\s*\|(.*)\|\s*$")

WIDTH = 100


def plain(text):
    """Strip the markdown a fixed-width sheet cannot show."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)   # links keep the label
    text = text.replace("**", "").replace("`", "").replace("*", "")
    text = text.replace("🔴", "!!").replace("✅", "OK").replace("→", "->")
    text = re.sub(r"<br\s*/?>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def boards_for(scope):
    """The scope line decides how many columns a step gets."""
    s = scope.lower()
    if "all five" in s:
        return [1, 2, 3, 4, 5]
    if "2 to 5" in s:
        return [2, 3, 4, 5]
    m = re.search(r"board (\d+)", s)
    if m:
        return [int(m.group(1))]
    return []          # bench work: one field, no board identity


def parse(path):
    phases, phase, section = [], None, None
    for line in path.read_text().splitlines():
        m = RE_PHASE.match(line)
        if m:
            phase = {"letter": m.group(1), "title": m.group(2),
                     "scope": "", "sections": []}
            phases.append(phase)
            section = None
            continue
        if phase is None:
            continue
        m = RE_SCOPE.match(line)
        if m:
            phase["scope"] = m.group(1)
            continue
        m = RE_SECTION.match(line)
        if m:
            section = {"id": m.group(1), "title": m.group(2), "steps": []}
            phase["sections"].append(section)
            continue
        m = RE_STEP.match(line)
        if m:
            cells = [plain(c) for c in m.group(2).split("|")]
            cells = [c for c in cells if c]
            if section is None:      # a step table before any ## heading
                section = {"id": phase["letter"], "title": "(unsectioned)",
                           "steps": []}
                phase["sections"].append(section)
            section["steps"].append({
                "id": m.group(1),
                "do": cells[0] if cells else "",
                "expect": " / ".join(cells[1:]) if len(cells) > 1 else "",
            })
    return phases


def wrap(text, width, indent):
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return ("\n" + " " * indent).join(out) if out else ""


def render(phases, date, wanted):
    L = [
        "caryatid bring-up tally sheet",
        "=" * WIDTH,
        "",
        f"  GENERATED {date} from docs/bringup.md by tools/gen_bringup_sheet.py.",
        "  BLANK. Nothing below is a result yet.",
        "",
        "  DO NOT EDIT THE RUNBOOK TO RECORD A READING, and do not hand-edit this",
        "  sheet's structure. Fix the runbook, regenerate, and the two stay in step.",
        "",
        "  Board: ............   Operator: ............   Started: ............",
        "",
        "  Instruments (per discovery/findings/bench-instruments.yaml):",
        "    meter  Fluke 101, NO current ranges. Current is a shunt voltage.",
        "    supply Jesverty 0-30 V 0-5 A, CC/OCP selectable.",
        "    shunts 10 ohm for mA, 0.1 ohm for ~1 A.",
        "",
    ]
    for ph in phases:
        if wanted and ph["letter"] not in wanted:
            continue
        boards = boards_for(ph["scope"])
        L += ["", "=" * WIDTH,
              f"PHASE {ph['letter']}: {ph['title'].upper()}",
              f"scope: {ph['scope']}", "=" * WIDTH, ""]
        for sec in ph["sections"]:
            if not sec["steps"]:
                continue
            L += [f"  {sec['id']}. {sec['title']}",
                  "  " + "-" * (len(sec["id"]) + len(sec["title"]) + 2), ""]
            for st in sec["steps"]:
                L.append(f"    {st['id']:<7} {wrap(st['do'], 84, 12)}")
                if st["expect"]:
                    L.append(f"            expect: {wrap(st['expect'], 76, 20)}")
                if boards:
                    L.append("            " + "  ".join(
                        f"b{b} ........" for b in boards))
                else:
                    L.append("            reading: ......................")
                L.append("")
        L += ["  NOTES / what this phase got wrong:",
              "  ..............................................................................",
              "  ..............................................................................", ""]
    L += ["", "=" * WIDTH,
          "WHAT WAS NOT TESTED. Fill this in, do not leave it blank.",
          "=" * WIDTH, "",
          "  Ripple, switching, inrush, debounce timing and audio quality are out of",
          "  reach with this kit. Anything else you skipped goes here, so the record",
          "  does not read as though it passed.", "",
          "  ..............................................................................",
          "  ..............................................................................", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", nargs="*", default=[],
                    help="phase letters to include, e.g. B C. Default all.")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    a = ap.parse_args()

    if not RUNBOOK.exists():
        sys.exit(f"runbook not found: {RUNBOOK}")
    phases = parse(RUNBOOK)
    if not phases:
        sys.exit("no phases parsed: has the runbook's heading convention changed?")
    wanted = [p.upper() for p in a.phase]
    unknown = set(wanted) - {p["letter"] for p in phases}
    if unknown:
        sys.exit(f"no such phase: {', '.join(sorted(unknown))}")

    text = render(phases, a.date, wanted)
    if a.stdout:
        print(text)
        return
    suffix = "-".join(wanted).lower() if wanted else "all"
    out = OUTDIR / f"{a.date}-bringup-sheet-{suffix}.txt"
    out.write_text(text)
    steps = sum(len(s["steps"]) for p in phases for s in p["sections"]
                if not wanted or p["letter"] in wanted)
    print(f"wrote {out.relative_to(ROOT)}  ({steps} steps, "
          f"{len([p for p in phases if not wanted or p['letter'] in wanted])} phases)")


if __name__ == "__main__":
    main()
