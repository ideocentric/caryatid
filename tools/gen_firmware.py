#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the firmware pin header from docs/pins.yaml.

    .venv/bin/python tools/gen_firmware.py            # rewrite the header
    .venv/bin/python tools/gen_firmware.py --check    # fail if stale

Same contract as gen_pinmap.py, and for the same reason: `docs/pins.yaml` is the
source of truth and everything else is a consumer of it. A pin map kept in two
places disagrees the first time a connector moves, and a firmware header is a
much worse place to find that out than a markdown table -- the board is already
built by then, and the symptom is a sensor reading the wrong wire.

WHAT IT EMITS
-------------
firmware/include/caryatid_pins.h -- one constant per physical pin, carrying the
Daisy Seed pin index, and comments carrying the caryatid name, the STM32 pin,
the connector and the role. The comments are the point: a number on its own
tells you nothing at a call site.

THE SEED INDEX IS NOT ALWAYS THE PIN NUMBER
-------------------------------------------
Analogue entries carry an explicit `seed:` field, because caryatid's A0 is the
Daisy Seed's pin 15. Digital entries do not, because there the two numbering
schemes coincide -- caryatid D7 is Seed pin 7. This generator handles both and
asserts the mapping is total; if a future pin has neither, it stops rather than
guessing, because a guess here silently reads the wrong pin.

LICENSING
---------
This generator is GPL-3.0-or-later like the rest of tools/. The header it emits
is MIT, so instrument firmware can link it without inheriting copyleft -- see
LICENSING.md. Generated output taking a different licence from its generator is
deliberate and normal: the output is not a derivative of the tool.
"""
import sys, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PINS = os.path.join(ROOT, "docs", "pins.yaml")
OUT = os.path.join(ROOT, "firmware", "include", "caryatid_pins.h")

HEADER = """\
// SPDX-License-Identifier: MIT
// caryatid -- pin definitions for the Daisy Seed carrier board
//
// GENERATED FROM docs/pins.yaml BY tools/gen_firmware.py -- DO NOT EDIT.
// Edit the yaml and regenerate:  .venv/bin/python tools/gen_firmware.py
//
// Values are DAISY SEED pin indices, ready for seed.GetPin(n). They are NOT
// the caryatid pin names: caryatid A0 is Seed pin 15. The caryatid name is in
// the comment on every line, because that is what the silkscreen, the
// schematic and docs/pinmap.md all use.
//
// THE PIN MAP IS FROZEN. An instrument may leave a pin unpopulated and may
// choose between the alternates listed, but may not repurpose one -- the whole
// value of the platform is that one PCB layout serves every build.

#pragma once

namespace caryatid {
"""

FOOTER = """
}  // namespace caryatid
"""


def load_pins():
    """Read pins.yaml with the venv's pyyaml, falling back to a hard error --
    this file is too important to parse with a regex."""
    try:
        import yaml
    except ImportError:
        sys.exit("  pyyaml required:  .venv/bin/pip install pyyaml")
    return yaml.safe_load(open(PINS))


def ident(role, pin):
    """A C identifier from the role text, disambiguated by pin where roles
    repeat (there are eight 'analog panel N')."""
    s = re.sub(r"[^a-z0-9]+", "_", role.lower()).strip("_")
    s = re.sub(r"^(analog|digital)_panel_(\d+)$", r"\1_panel_\2", s)
    return s.upper()


def seed_index(entry):
    """Seed pin index for an entry. Analogue carries `seed: D15`; digital's own
    number is the index. Anything else is a hard stop -- see module docstring."""
    if "seed" in entry:
        m = re.match(r"D(\d+)$", str(entry["seed"]))
        if not m:
            sys.exit(f"  unparseable seed field on {entry['pin']}: {entry['seed']}")
        return int(m.group(1))
    m = re.match(r"D(\d+)$", str(entry["pin"]))
    if not m:
        sys.exit(f"  {entry['pin']} has no `seed:` field and its name is not D<n>. "
                 f"Add an explicit mapping rather than letting this guess.")
    return int(m.group(1))


def emit(doc):
    lines = [HEADER]
    for section, title in (("analog", "Analogue -- all twelve ADC-capable pins"),
                           ("digital", "Digital")):
        lines.append(f"\n// {'-'*72}\n// {title}\n// {'-'*72}\n")
        width = max(len(ident(e["role"], e["pin"])) for e in doc[section])
        for e in doc[section]:
            name, idx = ident(e["role"], e["pin"]), seed_index(e)
            alt = f", alt {e['alt']}" if e.get("alt") else ""
            lines.append(
                f"constexpr int {name:<{width}} = {idx:>2};"
                f"  // {e['pin']:<4} {e['mcu']:<5} {e['connector']}{alt}\n")
    # Counts an instrument will otherwise hardcode and get wrong.
    n_panel_a = sum(1 for e in doc["analog"] if "analog panel" in e["role"])
    n_panel_d = sum(1 for e in doc["digital"] if "digital panel" in e["role"])
    lines.append(f"""
// {'-'*72}
// Bus widths. Hardcoding these at a call site is how a loop walks off the end.
// {'-'*72}

constexpr int ANALOG_PANEL_COUNT  = {n_panel_a};  // J5, in order on the connector
constexpr int DIGITAL_PANEL_COUNT = {n_panel_d};  // J11, in order on the connector

// J5 wipers in connector order -- pins 2-5 then 6-9, which is NOT A0..A7.
constexpr int ANALOG_PANEL[ANALOG_PANEL_COUNT] = {{
    {', '.join(ident(e['role'], e['pin'])
               for e in doc['analog'] if 'analog panel' in e['role'])}
}};

// J11 lines in connector order, pins 2-8.
constexpr int DIGITAL_PANEL[DIGITAL_PANEL_COUNT] = {{
    {', '.join(ident(e['role'], e['pin'])
               for e in doc['digital'] if 'digital panel' in e['role'])}
}};
""")
    lines.append(FOOTER)
    return "".join(lines)


def main():
    doc = load_pins()
    text = emit(doc)
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print(f"  MISSING {OUT}"); return 1
        cur = open(OUT).read()
        if cur != text:
            print("  STALE -- caryatid_pins.h does not match docs/pins.yaml")
            print("  regenerate:  .venv/bin/python tools/gen_firmware.py")
            return 1
        print(f"  up to date ({len(text.splitlines())} lines)")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(text)
    n = sum(len(doc[s]) for s in ("analog", "digital"))
    print(f"  wrote {os.path.relpath(OUT, ROOT)} -- {n} pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())