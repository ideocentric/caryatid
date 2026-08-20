#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR 0009 — put the mic front-end behind three jumpers, and populate it.

    .venv/bin/python tools/oneshot/add_mic_jumpers.py --apply

COORDINATES ARE ON THE 1.27 mm CONNECTION GRID. A first attempt used round
numbers (480.0, 140.0) and ERC returned 17 `endpoint_off_grid` warnings -- every
pin and stub missed the grid, which is how a connection silently fails to form.
Every X, Y and derived pin/label coordinate here is a multiple of 1.27.

ONE-SHOT. Run once, verify, commit. It is idempotent only in the sense that it
refuses to run twice: it checks for JP1 and stops if the edit is already in.

WHY THIS IS SAFE TO DO BY TEXT
------------------------------
The audio sheet is LABEL-CONNECTED, not wire-routed. Every part is a vertical
symbol with 5.08 mm pin stubs out to a named label, verified against J17 and
J18. So inserting a jumper into a net is a RENAME plus an ADD, not geometric
surgery:

    R51.2 --stub--> label "MIC_L"        becomes    label "BIAS_E_L"
                                         and JP1 carries BIAS_E_L / MIC_L / BIAS_C_L

The transform from library pin to sheet coordinate was confirmed against two
existing Conn_01x03 instances: sheet_x = X + lib_x, sheet_y = Y - lib_y.

WHAT IT DOES
------------
1. Splits three nets by renaming six labels.
2. Adds JP1/JP2/JP3 (Conn_01x03) and R67 (392R), each with pin stubs + labels.
3. Clears `dnp` on the left-channel front-end so it is assembled.
4. Clears `dnp` on R59/R60/R61 -- see below, this one is not cosmetic.

THE RIGHT-CHANNEL OP-AMP IS NOT OPTIONAL
----------------------------------------
U4 is a DUAL. Populating it for the left channel leaves section B's inputs
floating, and a floating op-amp input oscillates and draws current. R59/R60
(mid-rail to +in) and R61 (feedback out to -in) are therefore populated with
R62 left open, which makes section B a unity-gain follower sitting at VBIAS_R.
Three resistors to stop an unused amplifier misbehaving.

VERIFY AFTER RUNNING: ERC clean, and the netlist must show exactly the nets in
ADR 0009 and no others changed. The netlist diff is the real check -- ERC will
not notice a jumper wired to the wrong net.
"""
import sys, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(os.path.dirname(HERE), "..", "hardware", "pcb", "audio.kicad_sch")
SCH = os.path.normpath(SCH)
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
PATH = "/49c08c53-8a29-4df2-81cf-05d7b7c47990/bda31c7d-e5ef-4a38-8900-64d829b923ab"

# (old name, x, y, new name) -- coordinates identify WHICH label, since the
# same name appears many times.
RENAMES = [
    ("MIC_L",      110.49, 138.43, "BIAS_E_L"),   # R51.2, electret bias leg
    ("MIC_L",      139.70, 138.43, "BIAS_C_L"),   # R52.2, carbon bias leg
    ("GAINLEG_L",  219.71, 223.52, "LEG_101_L"),  # R58.2, the x101 leg
    ("AUDIO_IN_L", 325.12, 179.07, "AMP_OUT_L"),  # C25.2, op-amp output
    ("AUDIO_IN_L", 400.05, 218.44, "BYPASS_L"),   # R63.2, bypass series
    ("AUDIO_IN_L", 439.42, 200.66, "BYPASS_L"),   # R64.1, pad shunt tap
]

# ref, x, y, value, footprint, [(pin, label, global?)]
JUMPERS = [
    ("JP1", 480.06, 139.70, "Mic bias select", "PinHeader_1x03_P2.54mm_Vertical",
     [("1", "BIAS_E_L", False), ("2", "MIC_L", False), ("3", "BIAS_C_L", False)]),
    ("JP2", 480.06, 190.50, "Mic path select", "PinHeader_1x03_P2.54mm_Vertical",
     # All three GLOBAL: the labels these join were already global_label blocks,
     # and mixing a local and a global of the same name is an ERC warning even
     # though the nets do connect.
     [("1", "AMP_OUT_L", True), ("2", "AUDIO_IN_L", True), ("3", "BYPASS_L", True)]),
    ("JP3", 480.06, 241.30, "Mic gain select", "PinHeader_1x03_P2.54mm_Vertical",
     [("1", "LEG_101_L", False), ("2", "GAINLEG_L", False), ("3", "LEG_256_L", False)]),
]

# Left-channel front-end -> assembled. R64 stays DNP: it is the carbon pad's
# shunt and is fitted only if a measured capsule needs attenuating.
POPULATE = ["C22", "C23", "C24", "C25", "R51", "R52", "R55", "R56", "R57",
            "R58", "R63", "U4",
            "R59", "R60", "R61"]        # section-B follower, see docstring


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


def main():
    t = open(SCH).read()
    if '"JP1"' in t:
        sys.exit("  JP1 already present -- this edit is already applied. Stopping.")
    n_ren = 0
    for old, x, y, new in RENAMES:
        # match the label block whose name AND coordinates both agree
        pat = (r'(\((?:label|global_label) ")' + re.escape(old) + r'("[\s\S]{0,80}?\(at '
               + re.escape(f"{x} {y} ") + r'\d+\))')
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

    # R67: the x256 gain leg, hanging off OPA_L_N alongside R58
    add.append(symbol("Device:R", "R67", "392R",
                      "Resistor_SMD:R_0603_1608Metric", 530.86, 214.63, 2))
    add.append(wire(530.86, 210.82, 530.86, 205.74))
    add.append(label("OPA_L_N", 530.86, 205.74, 90, False, "left bottom"))
    add.append(wire(530.86, 218.44, 530.86, 223.52))
    add.append(label("LEG_256_L", 530.86, 223.52, 270, False, "left bottom"))

    close = t.rstrip().rfind("\n)")
    t = t[:close + 1] + "".join(add) + t[close + 1:]

    n_pop = 0
    for ref in POPULATE:
        for m in list(re.finditer(r'\n\t\(symbol\n', t))[::-1]:
            s = m.start() + 1
            d, j = 0, s
            while True:
                if t[j] == "(": d += 1
                elif t[j] == ")":
                    d -= 1
                    if d == 0: break
                j += 1
            blk = t[s:j + 1]
            if re.search(r'\(property "Reference" "' + re.escape(ref) + r'"', blk) \
                    and "\t\t(dnp yes)\n" in blk:
                t = t[:s] + blk.replace("\t\t(dnp yes)\n", "\t\t(dnp no)\n", 1) + t[j + 1:]
                n_pop += 1
    print(f"  renamed {n_ren} labels, added {len(JUMPERS)} jumpers + R67, "
          f"populated {n_pop} symbol instances")
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    print(f"  paren balance {d}")
    if d != 0: sys.exit("  UNBALANCED -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(SCH, "w").write(t)
    print(f"  wrote {SCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())