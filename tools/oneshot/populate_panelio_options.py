#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR 0010 — assemble the four panel-io circuit options.

    python3 tools/oneshot/populate_panelio_options.py --apply

    R43  4k7  +3V3 -> D12 (SDA)   I2C pull-up
    R44  4k7  +3V3 -> D11 (SCL)   I2C pull-up
    R45  3k   A5 -> GND           SoftPot pulldown
    R46  10k  A4 -> GND           FSR pulldown

WHY THESE FOUR ARE SAFE TO FIT ON EVERY BOARD
----------------------------------------------
They were DNP because each is wanted only in one of two mutually exclusive uses.
Neither exclusion survives contact with the actual numbers.

**The pull-ups do not spoil a UART.** J13/J19 share D11/D12 and the port may
carry I2C or a serial link. A UART line IDLES HIGH, so a 4k7 to +3V3 holds it
where it should already be; the only cost is 0.7 mA while a driver pulls it low,
against the 3.3 V rail on a board that budgets in tens of milliamps for the mic
bias alone. A floating RX with no pull-up is the worse of the two states.

**The pulldowns touch nothing else.** Checked against the netlist rather than
assumed: J5, the analogue bus, carries A0-A3 and A6-A9. A4 and A5 reach ONLY
J10 (FSR) and J9 (SoftPot), so a pulldown on either can affect no other input.
On an instrument that fits neither sensor the pin reads a defined 0 instead of
floating, which is strictly better than the DNP state.

Values are unchanged and remain the corrected assignment from pinmap.md -- 10k
on the FSR at A4, 3k on the SoftPot at A5. The platform spec had these
transposed, inherited from a stale ribbon-synth doc; the fabricated absonus
board is the evidence.

ONE-SHOT. Refuses to run twice: it stops if none of the four is still DNP.
"""
import sys, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "pcb",
                                    "panel-io.kicad_sch"))
POPULATE = ["R43", "R44", "R45", "R46"]


def blocks(t):
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
    n = 0
    for ref in POPULATE:
        for s, blk in list(blocks(t))[::-1]:
            if re.search(r'\(property "Reference" "' + re.escape(ref) + r'"', blk) \
                    and "\t\t(dnp yes)\n" in blk:
                t = (t[:s] + blk.replace("\t\t(dnp yes)\n", "\t\t(dnp no)\n", 1)
                     + t[s + len(blk):])
                print(f"    {ref} -> assembled")
                n += 1
    if n == 0:
        sys.exit("  none of R43-R46 is DNP -- this edit is already applied. Stopping.")
    print(f"  populated {n} symbols")
    d = sum(1 if c == "(" else -1 if c == ")" else 0 for c in t)
    if d != 0:
        sys.exit(f"  UNBALANCED ({d}) -- not writing")
    if "--apply" not in sys.argv:
        print("  dry run -- pass --apply to write")
        return 0
    open(SCH, "w").write(t)
    print(f"  wrote {SCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())