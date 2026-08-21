#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR 0010 step 2 — apply the schematic changes to the board.

    KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
    $KPY tools/oneshot/update_pcb_from_schematic.py            # writes a copy, verifies
    $KPY tools/oneshot/update_pcb_from_schematic.py --apply     # writes the board

MUST RUN UNDER KiCad's BUNDLED PYTHON, not the project .venv -- it needs
`pcbnew`. The interpreter path above is the whole reason this is awkward.

WHY THIS SCRIPT EXISTS AT ALL
------------------------------
"Update PCB from Schematic" is a GUI menu item. `kicad-cli` has no equivalent in
9.0.6, and the class the menu item drives -- BOARD_NETLIST_UPDATER -- is not
exposed to the Python bindings either (checked: `hasattr(pcbnew,
'BOARD_NETLIST_UPDATER')` is False).

So this reproduces its effect through the BOARD API. **That is not the same as
re-implementing it.** It applies one specific, enumerated set of changes -- the
28 differences KiCad's own `--schematic-parity` reports -- rather than
generally diffing a netlist against a board. Anything not in the lists below is
not touched.

THE 28 ITEMS, WHICH ARE KiCad'S LIST AND NOT MINE
--------------------------------------------------
    12  'Do not populate' settings differ    clear the DNP attribute
     5  net_conflict                          retarget the pad
     3  Value doesn't match symbol value      JP1-3 gained an " L" suffix
     4  missing_footprint                     add JP4, JP5, JP6, R68
     4  extra_footprint                       delete R48, R50, R64, R66

THE ACCEPTANCE TEST IS KiCad'S OWN, AND IT IS EXACT: after this runs,
`kicad-cli pcb drc --schematic-parity` must report **0** footprint errors, down
from 28. There is no partial credit and no judgement call in that number.

FIVE TRACKS DIE WITH THE DELETED FOOTPRINTS. They terminate on pads that are
about to stop existing, so leaving them would strand copper on a live net:

    R48.1  /audio/OUT_L_J   0.58 mm      R66.1  AUDIO_IN_R   1.78 mm
    R48.1  /audio/OUT_L_J   0.73 mm      R64.1  BYPASS_L     1.78 mm
    R50.1  /audio/OUT_R_J   1.65 mm

**A deleted pad can take a route with it, and that is the real hazard here.**
R48 was DNP but its PAD IS COPPER, so the router was free to use it as a
junction -- if OUT_L_J ran R47.2 -> R48.1 -> J17.1, removing the pad and its
stubs breaks a connection that DRC currently calls complete. This is the
cascade `e2a1fc7` warned about, where deleting one item orphaned what fed it.
So the check after this is not "unconnected is 0" -- it cannot be, the new
jumpers are unrouted by design -- it is that **every unconnected item names a
net this change created.** Anything else means a route was cut.

ROUTING IS NOT DONE HERE, DELIBERATELY. This lands the footprints, the nets and
the deletions. Placing copper between them is a separate step.
"""
import sys, os

sys.path.insert(0, "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
                   "Python.framework/Versions/3.9/lib/python3.9/site-packages")
try:
    import pcbnew
except ImportError:
    sys.exit("  needs KiCad's bundled python -- see the docstring for the path")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
PCB = os.path.join(ROOT, "hardware", "pcb", "caryatid.kicad_pcb")
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

# The audio sheet's instance uuid. A footprint path is /<sheet>/<symbol> -- the
# ROOT sheet uuid is not in it, which `c7f00e1` had to correct once already.
SHEET = "bda31c7d-e5ef-4a38-8900-64d829b923ab"

DNP_CLEAR = ["C26", "C27", "C28", "C29", "R53", "R54", "R62", "R65",
             "R43", "R44", "R45", "R46"]

RENAME = {"JP1": "Mic bias select L",
          "JP2": "Mic path select L",
          "JP3": "Mic gain select L"}

# ref, pad, the net the schematic gives it
RENET = [("C29", "2", "AMP_OUT_R"),
         ("R53", "2", "/audio/BIAS_E_R"),
         ("R54", "2", "/audio/BIAS_C_R"),
         ("R62", "2", "/audio/LEG_101_R"),
         ("R65", "2", "BYPASS_R")]

DELETE = ["R48", "R50", "R64", "R66"]

# ref, lib, footprint, symbol uuid, x, y, rot, value, {pad: net}
#
# ⚠ THESE COORDINATES ARE A PARKING SPOT, NOT A PLACEMENT DECISION.
#
# The obvious home -- outboard of the right channel, mirroring how JP1-3 sit
# beside the left -- does not exist. A free-space scan over every courtyard,
# pad, via and F.Cu track says there is **no clear site for three 1x03 headers
# in a row within 41.6 mm of the right block**; the first attempt at (186, 100)
# put JP4 on top of a 19.18 mm MIC_L run and a JP6 pad 0.098 mm from a GND via.
# The area reads empty on a courtyard-only check and is full of copper.
#
# Individually they fit at ~18 mm, but splitting the trio costs the thing ADR
# 0009 relies on: the three positions being read as one selector.
#
# So they are parked TOGETHER at the nearest clear 3-up site, keeping the left
# channel's 4.59 mm pitch, to be dragged into place during routing. R68 goes to
# the nearest clear 0603 site to its partner R62, 9.7 mm away.
ADD = [
    ("JP4", "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
     "8c746e8a-31dc-5de1-b90b-263783b60a64", 176.50, 57.50, 0, "Mic bias select R",
     {"1": "/audio/BIAS_E_R", "2": "/audio/MIC_R", "3": "/audio/BIAS_C_R"}),
    ("JP5", "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
     "6119fad4-8752-5ba4-b326-085bcb01a1d2", 181.09, 57.50, 0, "Mic path select R",
     {"1": "AMP_OUT_R", "2": "AUDIO_IN_R", "3": "BYPASS_R"}),
    ("JP6", "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
     "a77f3d76-e2dd-570d-bee6-948741849ab2", 185.68, 57.50, 0, "Mic gain select R",
     {"1": "/audio/LEG_101_R", "2": "/audio/GAINLEG_R", "3": "/audio/LEG_256_R"}),
    ("R68", "Resistor_SMD", "R_0603_1608Metric",
     "0e6a37c2-c613-51b6-9dce-4a5f5c7a126d", 186.00, 92.25, -90, "392R",
     {"1": "/audio/OPA_R_N", "2": "/audio/LEG_256_R"}),
]

NEW_NETS = ["/audio/BIAS_E_R", "/audio/BIAS_C_R", "AMP_OUT_R", "BYPASS_R",
            "/audio/LEG_101_R", "/audio/LEG_256_R"]

# THE CASCADE, CAUGHT AND REPAIRED. Deleting R48 severed /audio/OUT_L_J, and the
# first run of this script proved it -- one unconnected item between two TRACKS,
# no pad involved, which is the signature of a junction that has been removed.
#
# R48 was DNP, but a DNP pad is still copper and the router had used it as the
# junction. The run was:
#
#     R47.2 @171.8950 --track-- 170.8265 --stub-- [R48.1 pad @170.2430]
#                                          --stub-- 169.5163 --track-- west
#
# BOTH deleted stubs were load-bearing. One segment replaces them, along the
# same Y at the same 0.25 mm width, occupying the copper the pad used to.
BRIDGE = [("/audio/OUT_L_J", 169.5163, 85.4710, 170.8265, 85.4710, 0.25, "F.Cu")]


def net(board, name):
    """Existing net by name, created if the schematic has just invented it."""
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        print(f"      + net {name}")
    return n


def main():
    apply_ = "--apply" in sys.argv
    out = PCB if apply_ else os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "caryatid-updated.kicad_pcb")

    b = pcbnew.LoadBoard(PCB)
    print(f"  loaded {len(b.GetFootprints())} footprints")

    if b.FindFootprintByReference("JP4"):
        sys.exit("  JP4 already on the board -- already applied. Stopping.")

    # --- 1. tracks that terminate on pads about to be deleted ---------------
    doomed = {}
    for ref in DELETE:
        f = b.FindFootprintByReference(ref)
        if not f:
            sys.exit(f"  FAILED: {ref} is not on the board")
        for p in f.Pads():
            doomed[(ref, p.GetPadName())] = p.GetPosition()
    kill = []
    for tr in b.GetTracks():
        if tr.GetClass() != "PCB_TRACK":
            continue
        for end in (tr.GetStart(), tr.GetEnd()):
            if any(abs(end.x - pos.x) < 200000 and abs(end.y - pos.y) < 200000
                   for pos in doomed.values()):
                kill.append(tr)
                break
    for tr in kill:
        print(f"    - track {tr.GetNetname()} {pcbnew.ToMM(tr.GetLength()):.2f} mm")
        b.RemoveNative(tr)
    print(f"  removed {len(kill)} stub tracks")

    # --- 2. delete the four extra footprints --------------------------------
    for ref in DELETE:
        b.RemoveNative(b.FindFootprintByReference(ref))
        print(f"    - footprint {ref}")

    # --- 3. clear DNP -------------------------------------------------------
    n = 0
    for ref in DNP_CLEAR:
        f = b.FindFootprintByReference(ref)
        if not f:
            sys.exit(f"  FAILED: {ref} is not on the board")
        if f.IsDNP():
            f.SetDNP(False)
            n += 1
    print(f"  cleared DNP on {n} footprints")

    # --- 4. values ----------------------------------------------------------
    for ref, val in RENAME.items():
        b.FindFootprintByReference(ref).SetValue(val)
    print(f"  renamed {len(RENAME)} values")

    # --- 5. retarget the five conflicting pads ------------------------------
    #
    # AND DELETE WHAT THE OLD NET LEFT BEHIND. KiCad moves the PAD and leaves
    # the TRACKS, so every retargeted pad keeps a track arriving on its former
    # net -- copper joining two nets that are now distinct. That is a short, and
    # it is the failure `0491e70` caught by hand on the left channel; this run
    # produced six of them before this block existed. tools/stale_tracks.py
    # finds the same thing after the fact.
    stale = []
    for ref, padname, netname in RENET:
        f = b.FindFootprintByReference(ref)
        for p in f.Pads():
            if p.GetPadName() == padname:
                was, pos = p.GetNetname(), p.GetPosition()
                p.SetNet(net(b, netname))
                print(f"    {ref}.{padname}  {was} -> {netname}")
                for tr in b.GetTracks():
                    if tr.GetClass() != "PCB_TRACK" or tr.GetNetname() != was:
                        continue
                    if any(abs(end.x - pos.x) < 200000 and abs(end.y - pos.y) < 200000
                           for end in (tr.GetStart(), tr.GetEnd())):
                        stale.append((tr, ref, padname, was))
                break
        else:
            sys.exit(f"  FAILED: no pad {padname} on {ref}")
    for tr, ref, padname, was in stale:
        print(f"    - stale {was} track {pcbnew.ToMM(tr.GetLength()):.2f} mm "
              f"on {ref}.{padname}")
        b.RemoveNative(tr)
    print(f"  removed {len(stale)} stale tracks")

    # --- 6. add the four missing footprints ---------------------------------
    for ref, lib, fpname, uuid, x, y, rot, val, pads in ADD:
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), fpname)
        if fp is None:
            sys.exit(f"  FAILED to load {lib}:{fpname}")
        # FootprintLoad returns the footprint with a BARE name as its id. The
        # symbol says "Connector_PinHeader_2.54mm:PinHeader_1x03_...", so
        # without the library nickname parity reports a footprint mismatch on
        # every added part -- 4 of them, on the first run of this script.
        fp.SetFPID(pcbnew.LIB_ID(lib, fpname))
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot:
            fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH(f"/{SHEET}/{uuid}"))
        b.Add(fp)
        for p in fp.Pads():
            nm = pads.get(p.GetPadName())
            if nm is None:
                sys.exit(f"  FAILED: no net given for {ref}.{p.GetPadName()}")
            p.SetNet(net(b, nm))
        print(f"    + {ref} at ({x}, {y}) rot {rot}")

    # --- 7. repair the route the deleted pad was carrying -------------------
    for netname, x1, y1, x2, y2, w, layer in BRIDGE:
        tr = pcbnew.PCB_TRACK(b)
        tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        tr.SetWidth(pcbnew.FromMM(w))
        tr.SetLayer(b.GetLayerID(layer))
        tr.SetNet(net(b, netname))
        b.Add(tr)
        print(f"    ~ bridged {netname} ({x1}, {y1}) -> ({x2}, {y2})")

    # --- 8. R68's reference, the same nudge R67 needed ----------------------
    # The library default puts a 0603's reference 1.43 mm out, which clears its
    # own silk outline by 0.227 mm against a 0.25 mm rule. `0491e70` moved R67
    # to 1.8 for exactly this; R68 is the same footprint at the same -90
    # rotation and inherits the same defect, so it takes the same fix. This one
    # is NOT a parking artifact -- it travels with the part wherever it lands.
    fp = b.FindFootprintByReference("R68")
    r = fp.Reference()
    r.SetPosition(pcbnew.VECTOR2I(fp.GetPosition().x + pcbnew.FromMM(1.8),
                                  fp.GetPosition().y))
    print("    ~ R68 reference 1.43 -> 1.8 mm, clearing the 0.25 mm silk rule")

    # --- 9. refill the pours ------------------------------------------------
    # NOT COSMETIC, AND NOT OPTIONAL. Before this runs the GND pour still fills
    # the copper where JP4-JP6 and R68 have just landed, so their pads sit
    # inside it: the first verified run reported 87 violations -- 34
    # solder_mask_bridge, 20 clearance, 17 hole_clearance, 10 shorting_items --
    # essentially all of them the plane touching the new pads. It is the `B`
    # keystroke in the GUI, and it has to happen before any DRC number here
    # means anything.
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    print(f"  refilled {len(b.Zones())} zones")

    b.Save(out)
    print(f"  wrote {out}")
    if not apply_:
        print("  dry run -- pass --apply to write the real board")
    return 0


if __name__ == "__main__":
    sys.exit(main())
