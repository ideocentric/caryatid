#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the fabrication package, and refuse to pretend it is complete.

    python3 tools/fab_package.py                # report readiness only
    python3 tools/fab_package.py --apply        # write local/fab/ and a zip

WHAT GOES TO A FAB, AND WHAT MUST NOT
-------------------------------------
`kicad-cli pcb export gerbers` with no layer list plots EVERYTHING -- courtyard,
fab, adhesive, Eco1/Eco2, user comments. Those are internal drawing layers. A
fab that receives them may ignore them, or may not. This exports exactly the
ten layers a two-layer board needs and nothing else.

DNP IS NOT COSMETIC HERE
------------------------
32 of this board's 124 components are Do-Not-Populate by design -- the audio
network is fitted per instrument, per docs/audio.md. Both the BOM and the
position file are exported with --exclude-dnp. Without it the assembler places
thirty-two parts that should not be there, including U4 and every 'open'
resistor, and the first anyone knows is a board that behaves wrongly.

THE PART NUMBERS ARE THE GATE
-----------------------------
An assembly house cannot quote a BOM without supplier part numbers, and this
design has none in the schematic. hardware/pcb/lcsc.yaml carries the ones
docs/sourcing.md actually states; everything else is reported as a gap and the
tool exits nonzero. It does not fill blanks by guessing -- an invented LCSC
code does not fail loudly, it arrives as the wrong component.
"""
import sys, os, re, csv, json, subprocess, zipfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_board as C

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CLI = CLI if os.path.exists(CLI) else "kicad-cli"
PCB = C.PCB
SCH = os.path.join(os.path.dirname(PCB), "caryatid.kicad_sch")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PCB))), "local", "fab")
MAP = os.path.join(os.path.dirname(PCB), "lcsc.yaml")

LAYERS = ("F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,"
          "F.Paste,B.Paste,Edge.Cuts")


def load_map():
    """Minimal YAML reader for the shape this file actually has -- avoids a
    dependency for six blocks of key: {a: b} lines."""
    if not os.path.exists(MAP): return {}, {}, {}
    by_ref, by_fp, by_vf = {}, {}, {}
    section, pending = None, None
    for raw in open(MAP):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"): continue
        if not line.startswith((" ", "\t")):
            section = line.split(":")[0].strip(); pending = None; continue
        m = re.match(r'\s+"?([^":]+)"?:\s*(\{.*\})?\s*$', line)
        if m and m.group(2):
            key, body = m.group(1).strip(), m.group(2)
            val = re.search(r"lcsc:\s*(\S+?)[,}]", body)
            if val:
                d = {"lcsc": val.group(1)}
                {"by_ref": by_ref, "by_footprint": by_fp,
                 "by_value_footprint": by_vf}.get(section, {})[key] = d
            pending = None
        elif m:
            pending = m.group(1).strip()
        elif pending:
            val = re.search(r"lcsc:\s*(\S+?)[,}]", line)
            if val:
                {"by_ref": by_ref, "by_footprint": by_fp,
                 "by_value_footprint": by_vf}.get(section, {})[pending] = {"lcsc": val.group(1)}
            pending = None
    return by_ref, by_fp, by_vf


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print("  FAILED:", " ".join(cmd[:4]), r.stderr[:200]); sys.exit(1)
    return r


def main():
    apply_ = "--apply" in sys.argv
    tmp = "/tmp/caryatid-fab"
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)

    print("  exporting ...")
    run([CLI, "pcb", "export", "gerbers", "--layers", LAYERS,
         "--no-protel-ext", "--subtract-soldermask", "-o", tmp + "/", PCB])
    run([CLI, "pcb", "export", "drill", "--format", "excellon",
         "--drill-origin", "absolute", "--excellon-units", "mm",
         "--generate-map", "--map-format", "gerberx2", "-o", tmp + "/", PCB])
    run([CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
         "--side", "both", "--exclude-dnp", "-o", tmp + "/cpl.csv", PCB])
    run([CLI, "sch", "export", "bom", "--exclude-dnp",
         "--fields", "Reference,Value,Footprint,${QUANTITY}",
         "--group-by", "Value,Footprint", "-o", tmp + "/bom.csv", SCH])

    gerbers = sorted(f for f in os.listdir(tmp) if f.endswith((".gbr", ".drl")))
    print(f"  {len(gerbers)} fab files")
    for g in gerbers: print(f"      {g}")

    by_ref, by_fp, by_vf = load_map()
    rows = list(csv.DictReader(open(tmp + "/bom.csv")))
    out, missing, covered = [], [], 0
    for r in rows:
        refs = [x.strip() for x in r["Reference"].replace("-", ",").split(",")]
        fp = r["Footprint"].split(":")[-1]
        hit = (by_ref.get(refs[0]) or by_vf.get(f'{r["Value"]}|{fp}') or by_fp.get(fp))
        code = hit["lcsc"] if hit else ""
        if code: covered += int(r["QUANTITY"])
        else: missing.append((r["Reference"], r["Value"], fp, int(r["QUANTITY"])))
        out.append({**r, "LCSC": code})
    with open(tmp + "/bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["LCSC"])
        w.writeheader(); w.writerows(out)

    total = sum(int(r["QUANTITY"]) for r in rows)
    ncpl = len(open(tmp + "/cpl.csv").readlines()) - 1
    print(f"\n  BOM {len(rows)} lines / {total} parts to place (DNP excluded)")
    print(f"  CPL {ncpl} placements")
    print(f"  LCSC: {covered} of {total} parts covered, "
          f"{total - covered} without a part number\n")
    for ref, val, fp, q in missing:
        print(f"    no LCSC  {ref[:30]:<31} {val[:16]:<17} x{q}")

    if apply_:
        os.makedirs(OUT, exist_ok=True)
        z = os.path.join(OUT, "caryatid-fab.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(tmp)): zf.write(os.path.join(tmp, f), f)
        for f in ("bom.csv", "cpl.csv"): shutil.copy(os.path.join(tmp, f), OUT)
        print(f"\n  wrote {z} ({os.path.getsize(z)//1024} kB) and bom/cpl beside it")

    if missing:
        print(f"\n  NOT READY FOR ASSEMBLY: {total - covered} parts have no LCSC "
              f"number.\n  The bare boards can be ordered; the assembly cannot "
              f"be quoted.")
        return 1
    print("\n  ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())