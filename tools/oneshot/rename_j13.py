#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rename J13A -> J13 and J13B -> J19, because KiCad will not accept the old names.

    .venv/bin/python tools/oneshot/rename_j13.py            # report
    .venv/bin/python tools/oneshot/rename_j13.py --apply

WHY
---
KiCad parses a reference designator as PREFIX + NUMBER. "J13A" ends in a letter,
so KiCad reads the whole string as a prefix with no number and considers the
symbol UNANNOTATED. Consequences, all of which we hit:

  - the BOM exporter emitted "J13A?", which JLC rejected
  - "Update PCB from Schematic" refuses to run until the sheet is annotated,
    and accepting the annotation renames them to J13A1 / J13B1, which changes
    the references, breaks every footprint path, and makes all 131 components
    look like additions again

There is no way to keep the names. KiCad's annotation rules are not negotiable.

WHAT DOES NOT GET REWRITTEN
---------------------------
  discovery/evidence/    Append-only, dated evidence. Rewriting a snapshot to
                         match today's names would falsify what JLC actually
                         returned on 2026-08-19. The ledger rule exists for
                         exactly this.
  tools/fab_package.py   Its docstring explains WHY "J13A?" appeared. The
                         explanation needs the old name to make sense; a note
                         is appended instead.
"""
import sys, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = ("discovery/evidence", "local", ".git")
SKIP_FILES = ("tools/fab_package.py", "tools/oneshot/rename_j13.py")

# longest first; both are replaced in one pass so neither can re-match the other
SUBS = [(r"J13A", "J13"), (r"J13a", "J13"), (r"J13B", "J19"), (r"J13b", "J19")]


def files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True,
                         text=True).stdout.split()
    for f in out:
        if any(f.startswith(d) for d in SKIP_DIRS): continue
        if f in SKIP_FILES: continue
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p): continue
        yield f, p


def main():
    apply_ = "--apply" in sys.argv
    pat = re.compile("|".join(k for k, _ in SUBS))
    table = dict(SUBS)
    total, touched = 0, []
    for rel, p in files():
        try: t = open(p).read()
        except (UnicodeDecodeError, PermissionError): continue
        n = len(pat.findall(t))
        if not n: continue
        new = pat.sub(lambda m: table[m.group(0)], t)
        total += n
        touched.append((rel, n))
        if apply_: open(p, "w").write(new)
    for rel, n in sorted(touched): print(f"    {n:>2}  {rel}")
    print(f"\n  {total} replacements across {len(touched)} files")
    print(f"  skipped by design: {', '.join(SKIP_DIRS + SKIP_FILES)}")
    if not apply_:
        print("\n  dry run -- pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())