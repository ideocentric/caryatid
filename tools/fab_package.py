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


def write_jlc_cpl(src, dst, drop=()):
    """Rewrite KiCad's position export into JLC's CPL format.

    JLC rejected the raw KiCad file. Their template
    (local/reference/JLCSMT_Sample_CPL1.xlsx in the loa repo) is:

        Designator | Mid X      | Mid Y      | Layer | Rotation
        C1         | 95.0518mm  | 22.6822mm  | Top   | 270

    Every column name differs from KiCad's, the coordinates carry a `mm`
    suffix, Layer is capitalised, and Rotation is a plain number. KiCad emits
    `Ref,Val,Package,PosX,PosY,Rot,Side` with bare decimals, lowercase `top`
    and rotations that can be negative.

    COORDINATES ARE NOT TOUCHED. They stay in the same absolute frame as the
    Gerbers, which is what JLC aligns them against -- KiCad's Y is negative
    here because both the Gerbers and this file use a Y-up flip of KiCad's
    internal origin, and they agree. Making Y positive to look like the sample
    would move every part relative to the board.

    Only the five columns in the template are emitted. Val and Package are
    dropped: they are not in JLC's format, and a parser that failed on the
    header names is not the place to bet on extra columns being ignored.
    """
    rows = list(csv.DictReader(open(src)))
    out = []
    for r in rows:
        ref = r["Ref"].strip('"')
        if ref in drop: continue
        rot = float(r["Rot"]) % 360.0          # -90 -> 270
        out.append({
            "Designator": ref,
            "Mid X": f'{float(r["PosX"]):.4f}mm',
            "Mid Y": f'{float(r["PosY"]):.4f}mm',
            "Layer": "Top" if r["Side"].strip('"').lower() == "top" else "Bottom",
            "Rotation": f"{rot:g}",
        })
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Designator", "Mid X", "Mid Y",
                                          "Layer", "Rotation"])
        w.writeheader(); w.writerows(out)
    return out


def load_self_fit():
    """Refs the owner buys and solders, not the assembler. See lcsc.yaml.

    NOT the same thing as DNP. A DNP position has no component; these have one,
    fitted by hand. Keeping the distinction matters because DNP is exported to
    the assembler as an instruction and would be a lie here."""
    if not os.path.exists(MAP): return {}
    out, section = {}, None
    for raw in open(MAP):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"): continue
        if not line.startswith((" ", "\t")):
            section = line.split(":")[0].strip(); continue
        if section != "self_fit": continue
        m = re.match(r'\s+"?([^":]+)"?:\s*\{(.*)\}\s*$', line)
        if not m: continue
        body = m.group(2)
        src = re.search(r'source:\s*"([^"]*)"', body)
        note = re.search(r'note:\s*"([^"]*)"', body)
        out[m.group(1).strip()] = {"source": src.group(1) if src else "",
                                   "note": note.group(1) if note else ""}
    return out


def split_refs(field):
    """BOM reference fields group refs and may use ranges. Expand both, so a
    self-fit ref inside a grouped row is actually found rather than missed."""
    refs = []
    for tok in field.split(","):
        tok = tok.strip()
        m = re.match(r"^([A-Za-z]+)(\d+)\s*-\s*([A-Za-z]*)(\d+)$", tok)
        if m and (not m.group(3) or m.group(3) == m.group(1)):
            refs += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(4)) + 1)]
        elif tok:
            refs.append(tok)
    return refs


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
    self_fit = load_self_fit()
    rows = list(csv.DictReader(open(tmp + "/bom.csv")))
    out, missing, covered, pulled = [], [], 0, []
    for r in rows:
        refs = split_refs(r["Reference"])
        fp = r["Footprint"].split(":")[-1]
        hit = (by_ref.get(refs[0]) or by_vf.get(f'{r["Value"]}|{fp}') or by_fp.get(fp))
        code = hit["lcsc"] if hit else ""

        # Hand-fitted refs leave the assembly BOM. A grouped row keeps the rest
        # of its refs and loses only the count it actually lost.
        mine = [x for x in refs if x in self_fit]
        if mine:
            keep = [x for x in refs if x not in self_fit]
            for x in mine:
                pulled.append({"Reference": x, "Value": r["Value"], "Footprint": fp,
                               "LCSC": code, "Source": self_fit[x]["source"],
                               "Note": self_fit[x]["note"]})
            if not keep:
                continue
            r = {**r, "Reference": ",".join(keep), "QUANTITY": str(len(keep))}

        if code: covered += int(r["QUANTITY"])
        else: missing.append((r["Reference"], r["Value"], fp, int(r["QUANTITY"])))
        out.append({**r, "LCSC": code})
    with open(tmp + "/bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["LCSC"])
        w.writeheader(); w.writerows(out)

    # Every self-fit ref must have matched something. A typo here would
    # silently leave the part in the assembly order -- the exact failure this
    # is meant to prevent -- so it is an error, not a warning.
    unmatched = set(self_fit) - {p["Reference"] for p in pulled}
    if unmatched:
        print(f"\n  ERROR: self_fit names refs not in the BOM: {', '.join(sorted(unmatched))}")
        print(f"  Check hardware/pcb/lcsc.yaml. They may be DNP already, or misspelled.")
        return 1

    # Always convert to JLC's CPL format -- their parser rejects KiCad's column
    # names outright. Self-fit refs drop out here too, or the assembler is told
    # to place a part that is not on the BOM.
    cpl = write_jlc_cpl(tmp + "/cpl.csv", tmp + "/cpl.csv", drop=set(self_fit))
    if len(cpl) != sum(int(r["QUANTITY"]) for r in out):
        print(f"\n  ERROR: CPL has {len(cpl)} placements but the BOM totals "
              f"{sum(int(r['QUANTITY']) for r in out)}. They must agree.")
        return 1
    if pulled:
        with open(tmp + "/self-fit.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pulled[0].keys()))
            w.writeheader(); w.writerows(pulled)

    total = sum(int(r["QUANTITY"]) for r in out)
    ncpl = len(open(tmp + "/cpl.csv").readlines()) - 1
    print(f"\n  BOM {len(out)} lines / {total} parts to place (DNP excluded)")
    print(f"  CPL {ncpl} placements")
    print(f"  LCSC: {covered} of {total} parts covered, "
          f"{total - covered} without a part number\n")
    for ref, val, fp, q in missing:
        print(f"    no LCSC  {ref[:30]:<31} {val[:16]:<17} x{q}")

    if pulled:
        print(f"  {len(pulled)} part(s) pulled from the assembly order -- "
              f"YOU buy and solder these:")
        for p in pulled:
            print(f"    {p['Reference']:<6} {p['Value'][:22]:<23} {p['Source']}")
        print(f"  -> self-fit.csv. They are NOT DNP: the board is not complete "
              f"until they are fitted.")

    if apply_:
        os.makedirs(OUT, exist_ok=True)
        z = os.path.join(OUT, "caryatid-fab.zip")
        # self-fit.csv is the OWNER's shopping list, not a fab deliverable.
        # Shipping it would hand the assembler a list of parts they are
        # explicitly not fitting, which invites exactly the confusion this
        # whole mechanism exists to avoid.
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(tmp)):
                if f == "self-fit.csv": continue
                zf.write(os.path.join(tmp, f), f)
        for f in ("bom.csv", "cpl.csv", "self-fit.csv"):
            src = os.path.join(tmp, f)
            if os.path.exists(src): shutil.copy(src, OUT)
        extra = " + self-fit.csv (yours, not the fab's)" if pulled else ""
        print(f"\n  wrote {z} ({os.path.getsize(z)//1024} kB) and bom/cpl{extra} beside it")

    if missing:
        print(f"\n  NOT READY FOR ASSEMBLY: {total - covered} parts have no LCSC "
              f"number.\n  The bare boards can be ordered; the assembly cannot "
              f"be quoted.")
        return 1
    print("\n  ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())