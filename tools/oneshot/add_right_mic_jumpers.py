#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR 0010 — mirror the mic front-end jumpers onto the right channel.

    python3 tools/oneshot/add_right_mic_jumpers.py --apply

WHY THE RIGHT CHANNEL NEEDED THIS AND NOT MERELY POPULATING
------------------------------------------------------------
ADR 0009 fixed the left channel and said the right "keeps its DNP network for a
future stereo line-in build". Clearing that DNP without jumpers would have
reintroduced the exact defect 0009 was written against -- the right channel is
laid out as an EXACT MIRROR of the pre-jumper left, so its bias and path pairs
land on the same node and are mutually exclusive:

    R53 2k2 -> +3V3A  and  R54 220R -> +5V   both on MIC_R
    C29 op-amp out    and  R65 0R bypass     both on AUDIO_IN_R

Two exclusive pairs decided with a soldering iron. Three jumpers make them
selectable, and the mirror is exact enough that this script is the left-channel
script translated.

THE MIRROR IS +149.86 mm IN Y, AND THAT IS MEASURED, NOT CHOSEN
----------------------------------------------------------------
Every right-channel counterpart sits exactly 149.86 mm below its left twin --
R51/R53, R58/R62, C25/C29, R63/R65, C24/C28 all agree. 149.86 / 1.27 = 118, so
the translation lands every coordinate back on the connection grid, which is the
trap the left-channel run fell into first (round numbers gave 17
`endpoint_off_grid` warnings, and an off-grid pin is how a connection silently
fails to form).

ONE PART IS GENUINELY NEW, NOT A TRANSLATION. The right channel never had a x256
gain leg -- the left has R58 1k alongside R67 392R, the right had only R62 1k.
R68 392R is added so JP6 has a second position to select.

WHAT IT DOES
------------
1. Splits three nets by renaming five labels.
2. Adds JP4/JP5/JP6 (Conn_01x03) and R68 (392R), each with pin stubs + labels.
3. Clears `dnp` on the right-channel front-end so it is assembled.
4. Suffixes JP1-3's value with " L" -- with six jumpers on the board, "Mic bias
   select" alone no longer says which channel. The BOM groups by LCSC part
   number rather than value, so this splits no line.

RUN drop_open_positions.py FIRST. R66 taps AUDIO_IN_R at (439.42, 350.52), which
is downstream of where JP5 lands; if it is still present when this runs, the
deleted pad ends up on the wrong side of the jumper. This script checks.

ONE-SHOT. Refuses to run twice: it stops if JP4 is already present.

VERIFY AFTER RUNNING: ERC clean, and the netlist must show exactly the nets
below and no others changed. The netlist diff is the real check -- ERC will not
notice a jumper wired to the wrong net.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb",
                                    "audio.kicad_sch"))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
PATH = "/49c08c53-8a29-4df2-81cf-05d7b7c47990/bda31c7d-e5ef-4a38-8900-64d829b923ab"

DY = 149.86      # the left-to-right mirror, 118 grid steps

# (old name, x, y, new name) -- coordinates identify WHICH label, since the
# same name appears many times. Each is its left twin's coordinate plus DY.
RENAMES = [
    ("MIC_R",      110.49, 288.29, "BIAS_E_R"),   # R53.2, electret bias leg
    ("MIC_R",      139.70, 288.29, "BIAS_C_R"),   # R54.2, carbon bias leg
    ("GAINLEG_R",  219.71, 373.38, "LEG_101_R"),  # R62.2, the x101 leg
    ("AUDIO_IN_R", 325.12, 328.93, "AMP_OUT_R"),  # C29.2, op-amp output
    ("AUDIO_IN_R", 400.05, 368.30, "BYPASS_R"),   # R65.2, bypass series
]

# ref, x, y, value, footprint, [(pin, label, global?)]
JUMPERS = [
    ("JP4", 480.06, 289.56, "Mic bias select R", "PinHeader_1x03_P2.54mm_Vertical",
     [("1", "BIAS_E_R", False), ("2", "MIC_R", False), ("3", "BIAS_C_R", False)]),
    ("JP5", 480.06, 340.36, "Mic path select R", "PinHeader_1x03_P2.54mm_Vertical",
     # All three GLOBAL, matching JP2: the labels these join were already
     # global_label blocks, and mixing a local and a global of the same name is
     # an ERC warning even though the nets do connect.
     [("1", "AMP_OUT_R", True), ("2", "AUDIO_IN_R", True), ("3", "BYPASS_R", True)]),
    ("JP6", 480.06, 391.16, "Mic gain select R", "PinHeader_1x03_P2.54mm_Vertical",
     [("1", "LEG_101_R", False), ("2", "GAINLEG_R", False), ("3", "LEG_256_R", False)]),
]

# The right-channel front-end -> assembled. R59/R60/R61 were already populated
# by ADR 0009 to stop section B floating; they now become the working mid-rail
# reference and feedback resistor of a live channel rather than a follower's.
POPULATE = ["C26", "C27", "C28", "C29", "R53", "R54", "R62", "R65"]

RELABEL = {"JP1": "Mic bias select L",
           "JP2": "Mic path select L",
           "JP3": "Mic gain select L"}


def uid(*parts):
    return str(uuid.uuid5(NS, "|".join(str(p) for p in parts)))


def label(name, x, y, rot, is_global, just):
    if is_global:
        return (f'\t(global_label "{name}"\n\t\t(shape bidirectional)\n'
                f'\t\t(at {x} {y} {rot})\n\t\t(effects\n\t\t\t(font\n'
                f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n'
                f'\t\t)\n\t\t(uuid "{uid("gl", name, x, y)}")\n\t)\n')
    return (f'\t(label "{name}"\n\t\t(at {x} {y} {rot})\n\t\t(effects\n\t\t\t(font\n'
            f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n'
            f'\t\t(uuid "{uid("lb", name, x, y)}")\n\t)\n')


def wire(x1, y1, x2, y2):
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {x1} {y1}) (xy {x2} {y2})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(uuid "{uid("w", x1, y1, x2, y2)}")\n\t)\n')


def symbol(lib, ref, val, fp, x, y, npins):
    p = [f'\t(symbol\n\t\t(lib_id "{lib}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
         f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
         f'\t\t(dnp no)\n\t\t(uuid "{uid("sym", ref)}")\n']
    for name, value, dy, hide in (("Reference", ref, -12.0, False),
                                  ("Value", val, -9.0, False),
                                  ("Footprint", fp, 0.0, True),
                                  ("Datasheet", "~", 0.0, True),
                                  ("Description", "", 0.0, True)):
        px, py = (x + 6.0, y + dy) if not hide else (x, y)
        h = "\n\t\t\t\t(hide yes)" if hide else ""
        p.append(f'\t\t(property "{name}" "{value}"\n\t\t\t(at {px} {py} 0)\n'
                 f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
                 f'\t\t\t\t){h}\n\t\t\t)\n\t\t)\n')
    for n in range(1, npins + 1):
        p.append(f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid("pin", ref, n)}")\n\t\t)\n')
    p.append(f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
             f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n'
             f'\t\t\t)\n\t\t)\n\t)\n')
    return "".join(p)


def blocks(t):
    """Every top-level symbol block, as (start, text)."""
    for m in re.finditer(r'\n\t\(symbol\n', t):
        s = m.start() + 1
        d, j = 0, s
        while True:
            if t[j] == "(":
                d += 1
            elif t[j] == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        yield s, t[s:j + 1]


def main():
    t = open(SCH).read()
    if '"JP4"' in t:
        sys.exit("  JP4 already present -- this edit is already applied. Stopping.")
    if '"R66"' in t:
        sys.exit("  R66 is still in the sheet. Run drop_open_positions.py first --\n"
                 "  it taps AUDIO_IN_R downstream of where JP5 lands.")

    n_ren = 0
    for old, x, y, new in RENAMES:
        # match the label block whose name AND coordinates both agree. The
        # coordinate is matched loosely on the trailing digits because KiCad
        # writes 328.93000000000004 where the arithmetic here gives 328.93.
        pat = (r'(\((?:label|global_label) ")' + re.escape(old)
               + r'("[\s\S]{0,120}?\(at ' + re.escape(str(x)) + r' '
               + re.escape(str(y)) + r'0*\d* \d+\))')
        t2, k = re.subn(pat, lambda m: m.group(1) + new + m.group(2), t, count=1)
        if k != 1:
            sys.exit(f"  FAILED to rename {old} at ({x},{y}) -- found {k} matches")
        t, n_ren = t2, n_ren + 1

    add = []
    for ref, x, y, val, fp, pins in JUMPERS:
        add.append(symbol("Connector_Generic:Conn_01x03", ref, val,
                          "Connector_PinHeader_2.54mm:" + fp, x, y, 3))
        for num, name, is_glob in pins:
            ly = y - 2.54 + (int(num) - 1) * 2.54
            add.append(wire(x - 5.08, ly, x - 10.16, ly))
            add.append(label(name, x - 10.16, ly, 180, is_glob, "right"))

    # R68: the x256 gain leg, hanging off OPA_R_N alongside R62. Mirrors R67
    # exactly -- 214.63 + DY.
    add.append(symbol("Device:R", "R68", "392R",
                      "Resistor_SMD:R_0603_1608Metric", 530.86, 364.49, 2))
    add.append(wire(530.86, 360.68, 530.86, 355.60))
    add.append(label("OPA_R_N", 530.86, 355.60, 90, False, "left bottom"))
    add.append(wire(530.86, 368.30, 530.86, 373.38))
    add.append(label("LEG_256_R", 530.86, 373.38, 270, False, "left bottom"))

    close = t.rstrip().rfind("\n)")
    t = t[:close + 1] + "".join(add) + t[close + 1:]

    n_pop = 0
    for ref in POPULATE:
        for s, blk in list(blocks(t))[::-1]:
            if re.search(r'\(property "Reference" "' + re.escape(ref) + r'"', blk) \
                    and "\t\t(dnp yes)\n" in blk:
                t = (t[:s] + blk.replace("\t\t(dnp yes)\n", "\t\t(dnp no)\n", 1)
                     + t[s + len(blk):])
                n_pop += 1

    n_rel = 0
    for ref, val in RELABEL.items():
        for s, blk in list(blocks(t))[::-1]:
            if re.search(r'\(property "Reference" "' + re.escape(ref) + r'"', blk):
                new = re.sub(r'(\(property "Value" ")[^"]*(")', r'\g<1>' + val + r'\2',
                             blk, count=1)
                if new != blk:
                    t = t[:s] + new + t[s + len(blk):]
                    n_rel += 1

    print(f"  renamed {n_ren} labels, added {len(JUMPERS)} jumpers + R68, "
          f"populated {n_pop} symbols, relabelled {n_rel} left jumpers")
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"  paren balance {d}")
    if d != 0:
        sys.exit("  UNBALANCED -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(SCH, "w").write(t)
    print(f"  wrote {SCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())