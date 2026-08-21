#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draw the mic capsule jumper settings as an SVG.

    .venv/bin/python tools/gen_mic_svg.py            # print the path it would write
    .venv/bin/python tools/gen_mic_svg.py --apply

WHY NOT MERMAID
---------------
Mermaid was tried. Three stacked pin circles per jumper, nested in subgraphs, is
the obvious way to express this -- and Mermaid renders it at an aspect ratio of
nearly 8:1, because nested `direction` is ignored and everything stacks into an
unreadable column. Measured, not assumed: 1400 x 10993 px.

A diagram whose whole point is spatial arrangement should not be handed to a
layout engine that will rearrange it. This draws the pins where the pins are.

THE SOURCE IS THE SAME TABLE THE SILKSCREEN USES
------------------------------------------------
CONFIG below is the one description of what each capsule needs. The silkscreen
legend, docs/mic-configurations.md and this drawing all say the same thing
because they are all generated or transcribed from it -- and if it ever changes,
this file regenerates rather than drifting.

Colours are mid-tone deliberately: GitHub renders README SVGs on both light and
dark backgrounds and does not reliably honour prefers-color-scheme, so nothing
here depends on knowing which.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "docs", "img", "mic-configurations.svg")

# capsule -> (identification, [(jumper, shunted pair or None, what it does)])
CONFIG = [
    ("ELECTRET", "open at DC", [
        ("JP1", (1, 2), "2k2 → 3V3A"),
        ("JP2", (1, 2), "op-amp"),
        ("JP3", (1, 2), "×101"),
    ]),
    ("DYNAMIC", "150–600 Ω steady", [
        ("JP1", None, "no bias"),
        ("JP2", (1, 2), "op-amp"),
        ("JP3", (2, 3), "×256"),
    ]),
    ("CARBON", "50–300 Ω unstable", [
        ("JP1", (2, 3), "220R → 5 V"),
        ("JP2", (2, 3), "bypass"),
        ("JP3", None, "not used"),
    ]),
]

INK   = "#5b6472"   # readable on white and on dark
ACC   = "#3367d6"   # shunt fill
MUTE  = "#9aa3af"   # open pins
LABEL = "#7a8494"

# ROWH must clear the whole stack: pins (2 x PITCH) + body padding + the
# "1-2" line + the description beneath it, THEN the next row's body which
# starts 18 px above its pin 1. At 122 the descriptions overprinted the row
# below -- "2k2 -> 3V3A" landed inside DYNAMIC's JP1 body.
COLW, ROWH = 132, 156
X0, Y0 = 150, 78
PINR, PITCH = 9, 30


def glyph(cx, cy, pair):
    """One 3-pin header. cy is the centre of pin 1."""
    o = []
    body_h = PITCH * 2 + 36
    o.append(f'<rect x="{cx-24}" y="{cy-18}" width="48" height="{body_h}" '
             f'rx="5" fill="none" stroke="{INK}" stroke-width="2"/>')
    if pair:
        a, b = pair
        top = cy + (a - 1) * PITCH - 13
        o.append(f'<rect x="{cx-16}" y="{top}" width="32" '
                 f'height="{PITCH + 26}" rx="13" fill="{ACC}" opacity="0.18" '
                 f'stroke="{ACC}" stroke-width="2"/>')
    for i in range(3):
        y = cy + i * PITCH
        lit = bool(pair) and (i + 1) in pair
        o.append(f'<circle cx="{cx}" cy="{y}" r="{PINR}" '
                 f'fill="{ACC if lit else "none"}" '
                 f'stroke="{ACC if lit else MUTE}" stroke-width="2"/>')
        if i == 0:
            o.append(f'<text x="{cx-24-7}" y="{y+4}" text-anchor="end" '
                     f'font-family="ui-monospace,Menlo,monospace" font-size="11" '
                     f'fill="{LABEL}">1</text>')
    return "\n    ".join(o)


def build():
    w = X0 + COLW * 3 + 30
    h = Y0 + ROWH * 3 + 16
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f'<title>caryatid mic capsule jumper settings</title>']

    # column headers
    for j, (name, _, _) in enumerate(CONFIG[0][2]):
        x = X0 + COLW * j + 24
        s.append(f'<text x="{x}" y="34" text-anchor="middle" font-size="15" '
                 f'font-weight="600" fill="{INK}">{name}</text>')
    s.append(f'<text x="{X0 + COLW*0 + 24}" y="52" text-anchor="middle" '
             f'font-size="11" fill="{LABEL}">bias</text>')
    s.append(f'<text x="{X0 + COLW*1 + 24}" y="52" text-anchor="middle" '
             f'font-size="11" fill="{LABEL}">path</text>')
    s.append(f'<text x="{X0 + COLW*2 + 24}" y="52" text-anchor="middle" '
             f'font-size="11" fill="{LABEL}">gain</text>')

    for r, (cap, ident, jumpers) in enumerate(CONFIG):
        cy = Y0 + ROWH * r
        s.append(f'<text x="16" y="{cy+8}" font-size="16" font-weight="600" '
                 f'fill="{INK}">{cap}</text>')
        s.append(f'<text x="16" y="{cy+28}" font-size="11.5" '
                 f'fill="{LABEL}">{ident}</text>')
        if r:
            s.append(f'<line x1="10" y1="{cy-42}" x2="{X0+COLW*3-4}" '
                     f'y2="{cy-42}" stroke="{MUTE}" stroke-width="1" '
                     f'opacity="0.35"/>')
        for j, (name, pair, does) in enumerate(jumpers):
            cx = X0 + COLW * j + 24
            s.append("    " + glyph(cx, cy, pair))
            txt = f"{pair[0]}-{pair[1]}" if pair else "none"
            s.append(f'<text x="{cx}" y="{cy + PITCH*2 + 34}" '
                     f'text-anchor="middle" font-size="12.5" font-weight="600" '
                     f'font-family="ui-monospace,Menlo,monospace" '
                     f'fill="{ACC if pair else MUTE}">{txt}</text>')
            s.append(f'<text x="{cx}" y="{cy + PITCH*2 + 50}" '
                     f'text-anchor="middle" font-size="11" '
                     f'fill="{LABEL}">{does}</text>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    svg = build()
    if "--apply" not in sys.argv:
        print(f"  would write {os.path.relpath(OUT, os.path.dirname(HERE))} "
              f"({len(svg)} bytes)")
        print("  dry run -- pass --apply to write")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(svg)
    print(f"  wrote {os.path.relpath(OUT, os.path.dirname(HERE))} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())