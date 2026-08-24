#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the fabrication package, and refuse to pretend it is complete.

    python3 tools/fab_package.py                # report readiness only
    python3 tools/fab_package.py --apply        # write local/fab/ and a zip
    python3 tools/fab_package.py --apply --archive   # ... and keep a board PDF

WHAT GOES TO A FAB, AND WHAT MUST NOT
-------------------------------------
`kicad-cli pcb export gerbers` with no layer list plots EVERYTHING -- courtyard,
fab, adhesive, Eco1/Eco2, user comments. Those are internal drawing layers. A
fab that receives them may ignore them, or may not. This exports exactly the
ten layers a two-layer board needs and nothing else.

DNP, AND WHY THIS BOARD NO LONGER HAS ANY
-----------------------------------------
This once read "32 of this board's 124 components are DNP by design". ADR 0010
overturned that: DNP was an instruction to a person, and JLC fits the
through-hole parts too, so every DNP line was either a part nobody would fit or
a decision nobody had made. NOTHING on this board is DNP now, and
check_board.py check 12 fails if anything becomes so.

The --exclude-dnp flags stay on both exports. They are now a guard rather than a
filter: if a dnp ever reappears, the assembler must not place it, and the export
should not have to be revisited to notice.

WHAT REPLACED IT IS self_fit, WHICH IS NOT THE SAME THING. BT1 is bought and
soldered by hand -- Digi-Key beat JLC's pre-order on both price and lead time --
so it is pulled from the assembly order into self-fit.csv. A DNP part is one the
board is complete without. A self-fit part is one the board is NOT complete
without, and conflating them ships an unpopulated battery holder.

AND ACCESSORIES ARE A THIRD CATEGORY AGAIN, WHICH A BOM CANNOT SEE.
A self-fit part is on the BOM and pulled out of the assembly order. An accessory
was never on the BOM, because it is not soldered to the board and a netlist has
no way to know it exists. The six jumper shunts JP1-JP6 need are the case that
found this: discussed in six documents, sourced in none, while this tool
reported "ready". A readiness report that covers only what the assembler fits is
not a readiness report. They are listed from lcsc.yaml `accessories:` with a
per-board quantity, and they go to the owner's shopping list, never to the fab.

THE BOARD PDF, AND WHY --archive IS SEPARATE
-------------------------------------------
--apply writes a nine-page reference plot to local/fab/, one page per layer with
the outline on every page, so the board can be read without KiCad. local/ is
gitignored and that copy is disposable: it regenerates from the board in a
second, and a file that regenerates is not an artefact.

--archive copies it to discovery/evidence/ under a DATED, SHA-STAMPED name, and
that copy is meant to be committed. Use it when an order is placed. The point is
not the picture, it is being able to answer "what exactly did we buy" in five
years without a KiCad install and without checking out an old commit to find
out. The SHA is the board's last-changed commit rather than HEAD, because HEAD
moves for documentation and the board does not.

THE PART NUMBERS ARE THE GATE
-----------------------------
An assembly house cannot quote a BOM without supplier part numbers, and this
design has none in the schematic. hardware/pcb/lcsc.yaml carries the ones
docs/sourcing.md actually states; everything else is reported as a gap and the
tool exits nonzero. It does not fill blanks by guessing -- an invented LCSC
code does not fail loudly, it arrives as the wrong component.
"""
import sys, os, re, csv, json, subprocess, zipfile, shutil, collections

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

# Human-readable reference plot. One page per layer with the outline on every
# page, so the board can be read without KiCad. NOT a fab deliverable: the
# gerbers are what gets manufactured, and this is for the shelf and the eye.
PDF_LAYERS = "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,F.Fab,B.Fab"
PDF_COMMON = "Edge.Cuts"


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


def board_sha():
    """Short SHA of the commit that last changed the BOARD, not HEAD.

    HEAD moves for documentation; the board does not. Naming the artefact after
    HEAD would imply a board changed when only prose did, and two snapshots of
    the same copper would carry different names."""
    r = subprocess.run(["git", "log", "-1", "--format=%h", "--", PCB],
                       cwd=os.path.dirname(PCB), capture_output=True, text=True)
    return (r.stdout.strip() or "nogit")


def board_pdf(dst):
    """Multi-page reference plot of the board.

    --mode-multipage treats -o as a DIRECTORY and names the file after the
    board, which is not what the rest of this tool assumes. Export into a
    scratch directory, then move the one file out under the name we wanted."""
    stage = dst + ".stage"
    shutil.rmtree(stage, ignore_errors=True)
    subprocess.run([CLI, "pcb", "export", "pdf", "--mode-multipage",
                    "--layers", PDF_LAYERS, "--common-layers", PDF_COMMON,
                    "--include-border-title", "--subtract-soldermask",
                    "-o", stage, PCB], check=True, capture_output=True)
    made = [f for f in os.listdir(stage) if f.endswith(".pdf")]
    if len(made) != 1:
        sys.exit(f"  PDF export produced {len(made)} files, expected 1")
    shutil.move(os.path.join(stage, made[0]), dst)
    shutil.rmtree(stage, ignore_errors=True)
    return dst


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


def load_accessories():
    """Parts on no BOM, bought by the owner and fitted after assembly.

    Keyed by a NAME, not a reference designator, because there is no designator
    to key on -- a shunt is not a placed component. Nothing here is matched
    against the BOM or pulled from the assembly order; the quantity is derived
    from per_board instead."""
    if not os.path.exists(MAP): return {}
    out, section = {}, None
    for raw in open(MAP):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"): continue
        if not line.startswith((" ", "\t")):
            section = line.split(":")[0].strip(); continue
        if section != "accessories": continue
        m = re.match(r'\s+"?([^":]+)"?:\s*\{(.*)\}\s*$', line)
        if not m: continue
        body = m.group(2)
        src = re.search(r'source:\s*"([^"]*)"', body)
        per = re.search(r'per_board:\s*(\d+)', body)
        note = re.search(r'note:\s*"([^"]*)"', body)
        out[m.group(1).strip()] = {
            "source": src.group(1) if src else "",
            "per_board": int(per.group(1)) if per else 0,
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
    archive = "--archive" in sys.argv
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
    # Flat: ONE ROW PER PART, no --group-by. KiCad's grouping compresses
    # references into ranges -- "C2-C5", "R27-R33" -- and JLC rejects those:
    # it wants every designator listed. Grouping is done below instead, where
    # the designator list is under our control.
    run([CLI, "sch", "export", "bom", "--exclude-dnp",
         "--fields", "Reference,Value,Footprint", "-o", tmp + "/bom.csv", SCH])

    gerbers = sorted(f for f in os.listdir(tmp) if f.endswith((".gbr", ".drl")))
    print(f"  {len(gerbers)} fab files")
    for g in gerbers: print(f"      {g}")

    by_ref, by_fp, by_vf = load_map()
    self_fit = load_self_fit()
    accessories = load_accessories()

    # The BOARD is the authority on reference names. pcbnew stores them
    # literally; the schematic BOM exporter does not. It parses a reference as
    # prefix+number, so "J13A" -- ending in a letter -- reads as UNANNOTATED and
    # comes out as "J13A?". The schematic is fine and DRC parity is clean; only
    # the exporter is confused. Reconciling against the board fixes it without
    # blindly stripping a "?" that might have meant something.
    #
    # FIXED AT SOURCE 2026-08-21: J13A/J13B are now J13/J19. The old names also
    # made KiCad demand annotation on every "Update PCB from Schematic", and
    # accepting it renamed them again and broke every footprint path. This
    # reconciliation stays because it costs nothing and would catch a recurrence.
    board_refs = set()
    for m in re.finditer(r'\(property "Reference" "([^"]+)"', open(PCB).read()):
        board_refs.add(m.group(1))

    rows = list(csv.DictReader(open(tmp + "/bom.csv")))
    groups, missing, covered, pulled, unknown = {}, [], 0, [], []
    for r in rows:
        raw = r["Reference"].strip()
        ref = raw[:-1] if raw.endswith("?") and raw[:-1] in board_refs else raw
        if ref not in board_refs:
            unknown.append(raw)
            continue
        fp = r["Footprint"].split(":")[-1]
        hit = (by_ref.get(ref) or by_vf.get(f'{r["Value"]}|{fp}') or by_fp.get(fp))
        code = hit["lcsc"] if hit else ""

        if ref in self_fit:
            pulled.append({"Reference": ref, "Value": r["Value"], "Footprint": fp,
                           "LCSC": code, "Source": self_fit[ref]["source"],
                           "Note": self_fit[ref]["note"]})
            continue

        # GROUP BY PART NUMBER, not by value. Six connectors on this board
        # share an LCSC code while carrying different roles as their value --
        # "DC in", "SW1 switch", "FSR" -- and grouping on value split one
        # orderable part across six lines. JLC then flags "Multiple lines in
        # the BOM", matches only the first, and assigns it QUANTITY ZERO, so
        # those parts are silently not assembled. One line per part number.
        key = code or (r["Value"], fp)
        g = groups.setdefault(key, {"values": [], "footprints": [],
                                    "JLCPCB Part #": code, "refs": []})
        g["refs"].append(ref)
        if r["Value"] not in g["values"]: g["values"].append(r["Value"])
        if fp not in g["footprints"]: g["footprints"].append(fp)

    if unknown:
        print(f"\n  ERROR: {len(unknown)} BOM reference(s) not found on the board: "
              f"{', '.join(unknown[:8])}")
        print(f"  The schematic and the board disagree. Run DRC with "
              f"--schematic-parity before shipping this.")
        return 1

    def sortkey(ref):
        m = re.match(r"^([A-Za-z]+)(\d*)(.*)$", ref)
        return (m.group(1), int(m.group(2) or 0), m.group(3))

    out = []
    for key, g in groups.items():
        g["refs"].sort(key=sortkey)
        n = len(g["refs"])
        code = g["JLCPCB Part #"]
        # One part, several roles -> keep them all, they are the only human
        # clue to what the line is for. Capped so a long join cannot upset
        # the parser.
        comment = " / ".join(g["values"])
        if len(comment) > 60: comment = comment[:57] + "..."
        fp = g["footprints"][0]
        if code: covered += n
        else: missing.append((",".join(g["refs"]), comment, fp, n))
        out.append({"Comment": comment,
                    "Designator": ",".join(g["refs"]),   # every one, no ranges
                    "Footprint": fp,
                    "JLCPCB Part #": code,
                    "QUANTITY": str(n)})
    out.sort(key=lambda r: sortkey(r["Designator"].split(",")[0]))

    # JLC's template is exactly four columns -- Sample-BOM_JLCSMT.xlsx. QUANTITY
    # is carried in memory for the reports and dropped on the way out.
    with open(tmp + "/bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint",
                                          "JLCPCB Part #"], extrasaction="ignore")
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

    # THE CHECK JLC ACTUALLY RUNS, and the one that rejected this package:
    # "designators don't exist in the BOM file" / "...in the CPL file". Every
    # designator must appear in both, exactly once. Counting alone would miss a
    # swap, so compare the sets in both directions.
    b_refs = [x.strip() for r in out for x in r["Designator"].split(",")]
    c_refs = [r["Designator"] for r in cpl]
    B, C = set(b_refs), set(c_refs)
    dupes = sorted({x for x in b_refs if b_refs.count(x) > 1})
    if B - C or C - B or dupes or len(b_refs) != len(c_refs):
        print(f"\n  ERROR: BOM and CPL disagree -- JLC will reject this.")
        if B - C: print(f"    in BOM, not CPL: {', '.join(sorted(B - C)[:12])}")
        if C - B: print(f"    in CPL, not BOM: {', '.join(sorted(C - B)[:12])}")
        if dupes: print(f"    duplicated in BOM: {', '.join(dupes[:12])}")
        return 1
    bad = [x for x in b_refs if "-" in x or "?" in x]
    if bad:
        print(f"\n  ERROR: designators still carry a range or '?': "
              f"{', '.join(bad[:12])}")
        return 1

    # ONE LINE PER PART NUMBER. JLC responds to a repeated part number with
    # "Multiple lines in the BOM", matches only the first occurrence and gives
    # it quantity ZERO -- so the part is quietly left unassembled rather than
    # rejected. That is far worse than an error, and it is invisible unless
    # you read their returned spreadsheet. Six connectors failed this way.
    seen = collections.Counter(r["JLCPCB Part #"] for r in out if r["JLCPCB Part #"])
    repeated = [c for c, k in seen.items() if k > 1]
    if repeated:
        print(f"\n  ERROR: {len(repeated)} part number(s) on more than one BOM "
              f"line: {', '.join(repeated[:8])}")
        print(f"  JLC will assign quantity 0 and not fit them. Group by part "
              f"number, not by value.")
        return 1
    if pulled:
        with open(tmp + "/self-fit.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pulled[0].keys()))
            w.writeheader(); w.writerows(pulled)

    board_pdf(tmp + "/caryatid-board.pdf")

    if accessories:
        with open(tmp + "/accessories.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Item", "PerBoard", "Source", "Note"])
            w.writeheader()
            for name, a in sorted(accessories.items()):
                w.writerow({"Item": name, "PerBoard": a["per_board"],
                            "Source": a["source"], "Note": a["note"]})

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

    if accessories:
        print(f"\n  {len(accessories)} accessory line(s) on NO bill of materials -- "
              f"YOU buy these too:")
        for name, a in sorted(accessories.items()):
            print(f"    {name:<14} {a['per_board']}/board   {a['source']}")
        print(f"  -> accessories.csv. A BOM cannot see these: they are not "
              f"soldered to the board, so nothing places them and nothing "
              f"misses them either.")

    if apply_:
        os.makedirs(OUT, exist_ok=True)
        z = os.path.join(OUT, "caryatid-fab.zip")
        # self-fit.csv is the OWNER's shopping list, not a fab deliverable.
        # Shipping it would hand the assembler a list of parts they are
        # explicitly not fitting, which invites exactly the confusion this
        # whole mechanism exists to avoid.
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(os.listdir(tmp)):
                if f in ("self-fit.csv", "accessories.csv",
                         "caryatid-board.pdf"): continue
                zf.write(os.path.join(tmp, f), f)
        for f in ("bom.csv", "cpl.csv", "self-fit.csv", "accessories.csv",
                  "caryatid-board.pdf"):
            src = os.path.join(tmp, f)
            if os.path.exists(src): shutil.copy(src, OUT)
        yours = [n for n, c in (("self-fit.csv", pulled),
                                ("accessories.csv", accessories)) if c]
        yours.append("caryatid-board.pdf")
        extra = f" + {' + '.join(yours)} (yours, not the fab's)" if yours else ""

        if archive:
            ev = os.path.join(os.path.dirname(os.path.dirname(PCB)),
                              "..", "discovery", "evidence")
            ev = os.path.normpath(ev)
            os.makedirs(ev, exist_ok=True)
            stamp = subprocess.run(["git", "log", "-1", "--format=%ad",
                                    "--date=format:%Y-%m-%d", "--", PCB],
                                   cwd=os.path.dirname(PCB),
                                   capture_output=True, text=True).stdout.strip()
            name = f"{stamp or 'undated'}-board-snapshot-{board_sha()}.pdf"
            target = os.path.join(ev, name)
            shutil.copy(os.path.join(OUT, "caryatid-board.pdf"), target)
            kb = os.path.getsize(target) // 1024
            print(f"\n  ARCHIVED {name} ({kb} kB) into discovery/evidence/")
            print(f"  Dated by the board's last change, not by today, so re-running")
            print(f"  produces the same filename until the copper actually moves.")
            print(f"  COMMIT IT: local/fab/ is gitignored and this is the copy that lasts.")
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