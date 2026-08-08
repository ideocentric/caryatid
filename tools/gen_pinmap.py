#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate docs/pinmap.md from docs/pins.yaml.

The map exists once, in YAML, and the human-readable table is derived. Writing
both by hand is how a pin map ends up disagreeing with itself -- which is the
specific failure this project has already paid for elsewhere.

    python3 tools/gen_pinmap.py           # rewrite docs/pinmap.md
    python3 tools/gen_pinmap.py --check   # fail if it is stale (for CI)

No dependencies. The YAML subset used here is small and fixed, so it is parsed
directly rather than pulling PyYAML in for one file -- a platform repo that
needs a virtualenv to read its own pin map is a platform repo nobody reads.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "pins.yaml"
OUT = ROOT / "docs" / "pinmap.md"


def parse_entries(text, section):
    """Pull the inline-mapping list items out of one top-level section."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == f"{section}:")
    except StopIteration:
        return []

    entries, buf, depth = [], "", 0
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not buf and line and not line[0].isspace() and stripped.endswith(":"):
            break                                     # next top-level section
        if not stripped or stripped.startswith("#"):
            continue
        if not buf and not stripped.startswith("- {"):
            continue
        buf += " " + stripped.lstrip("- ") if buf else stripped[2:]
        depth = buf.count("{") - buf.count("}")
        if depth == 0:
            entries.append(parse_inline(buf))
            buf = ""
    return entries


def parse_inline(s):
    """`{k: v, k: "v, with comma"}` -> dict. Quotes protect commas and colons."""
    s = s.strip().lstrip("{").rstrip("}")
    out, key, val, quote, esc = {}, None, "", None, False
    for ch in s + ",":
        if esc:
            val += ch; esc = False; continue
        if ch == "\\":
            esc = True; continue
        if quote:
            if ch == quote:
                quote = None
            else:
                val += ch
            continue
        if ch in "\"'":
            quote = ch; continue
        if ch == ":" and key is None:
            key, val = val.strip(), ""; continue
        if ch == ",":
            if key is not None:
                out[key] = re.sub(r"\s+", " ", val).strip()
            key, val = None, ""
            continue
        val += ch
    return out


def render(text):
    meta = {}
    for field in ("board", "mcu", "module", "revision", "status"):
        m = re.search(rf"^{field}:\s*(.+)$", text, re.M)
        if m:
            meta[field] = m.group(1).strip()

    lines = [
        "# Pin map",
        "",
        "<!-- GENERATED FROM docs/pins.yaml BY tools/gen_pinmap.py -- DO NOT EDIT -->",
        "",
        f"**{meta.get('board', '?')}** rev {meta.get('revision', '?')} — "
        f"{meta.get('module', '?')} ({meta.get('mcu', '?')}). "
        f"Status: **{meta.get('status', '?')}**.",
        "",
        "Frozen means an instrument may leave a pin unpopulated, and may choose",
        "between the alternates listed, but may not repurpose it. One PCB layout",
        "serves every build; only the population changes.",
        "",
    ]

    for section, title in (("analog", "Analogue"), ("digital", "Digital")):
        rows = parse_entries(text, section)
        if not rows:
            continue
        lines += [f"## {title}", "",
                  "| Pin | Seed | MCU | Role | Connector | Alternate |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for r in rows:
            pin = r.get("pin", "")
            lines.append("| `{}` | {} | {} | {} | {} | {} |".format(
                pin, r.get("seed", pin), r.get("mcu", ""), r.get("role", ""),
                r.get("connector", ""), f"`{r['alt']}`" if r.get("alt") else "—"))
        lines.append("")
        notes = [(r.get("pin", ""), r["notes"]) for r in rows if r.get("notes")]
        if notes:
            lines.append("**Notes**")
            lines.append("")
            lines += [f"- **`{p}`** — {n}" for p, n in notes]
            lines.append("")

    rows = parse_entries(text, "analog") + parse_entries(text, "digital")
    a, d = len(parse_entries(text, "analog")), len(parse_entries(text, "digital"))
    spare = [r["pin"] for r in rows if "spare" in r.get("role", "").lower()]
    lines += ["## Counts", "",
              f"- {a} analogue, {d} digital — **{a + d} of 31 Seed pins assigned**",
              f"- Spare: {', '.join(f'`{p}`' for p in spare) if spare else '**none**'}",
              "- Every other pin has a job. Adding one means taking it from "
              "something, which is what freezing the map is for.",
              ""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if pinmap.md is stale")
    args = ap.parse_args()

    if not SRC.exists():
        sys.exit(f"missing {SRC}")
    want = render(SRC.read_text())

    if args.check:
        have = OUT.read_text() if OUT.exists() else ""
        if have != want:
            sys.exit("docs/pinmap.md is stale -- run tools/gen_pinmap.py")
        print("pinmap.md is current")
        return

    OUT.write_text(want)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()