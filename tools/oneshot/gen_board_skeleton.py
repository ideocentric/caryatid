#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Created hardware/pcb/caryatid.kicad_pcb as an empty mechanical shell.

Board outline, four M3 holes, and the 2-layer stackup -- nothing else. The 125
footprints are NOT placed here: kicad-cli has no "update PCB from schematic", so
that import happens in the GUI (Tools > Update PCB from Schematic, F8).

Do not run again. Once footprints and traces exist, re-running discards them.
"""
import os, sys, uuid, re
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot, would discard the whole board")
KFP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
PCB=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","hardware","pcb")
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS,"caryatid-board:"+":".join(map(str,k))))

W,H = 150.0, 90.0            # long axis is X; BT1 gets 35 mm clear per end
# 90 is unchanged and proven against the BUD; all growth is on the long axis,
# where the conservative working rectangle leaves 165.1 - 150 = 15 mm spare.
OX,OY = 50.0, 30.0           # page origin offset, keeps the board off the margin
HOLES=[(5,5),(145,5),(5,85),(145,85)]

LAYERS="""	(layers
		(0 "F.Cu" signal)
		(31 "B.Cu" signal)
		(32 "B.Adhes" user "B.Adhesive")
		(33 "F.Adhes" user "F.Adhesive")
		(34 "B.Paste" user)
		(35 "F.Paste" user)
		(36 "B.SilkS" user "B.Silkscreen")
		(37 "F.SilkS" user "F.Silkscreen")
		(38 "B.Mask" user)
		(39 "F.Mask" user)
		(40 "Dwgs.User" user "User.Drawings")
		(41 "Cmts.User" user "User.Comments")
		(42 "Eco1.User" user "User.Eco1")
		(43 "Eco2.User" user "User.Eco2")
		(44 "Edge.Cuts" user)
		(45 "Margin" user)
		(46 "B.CrtYd" user "B.Courtyard")
		(47 "F.CrtYd" user "F.Courtyard")
		(48 "B.Fab" user)
		(49 "F.Fab" user)
	)"""

def line(x1,y1,x2,y2,layer="Edge.Cuts",w=0.1,tag=""):
    return (f'\t(gr_line\n\t\t(start {x1+OX} {y1+OY})\n\t\t(end {x2+OX} {y2+OY})\n'
            f'\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{U("l",tag,x1,y1,x2,y2)}")\n\t)\n')

def text(s,x,y,layer="Cmts.User",size=2.0):
    return (f'\t(gr_text "{s}"\n\t\t(at {x+OX} {y+OY} 0)\n\t\t(layer "{layer}")\n'
            f'\t\t(uuid "{U("t",s,x,y)}")\n\t\t(effects\n\t\t\t(font\n'
            f'\t\t\t\t(size {size} {size})\n\t\t\t\t(thickness {size/6:.2f})\n\t\t\t)\n\t\t)\n\t)\n')

def mounting_hole(x,y,i):
    src=open(os.path.join(KFP,"MountingHole.pretty","MountingHole_3.2mm_M3.kicad_mod")).read()
    src=re.sub(r'^\(footprint "([^"]+)"', r'(footprint "MountingHole:MountingHole_3.2mm_M3"', src, count=1)
    body=src[src.index("\n")+1:src.rindex(")")]
    body=re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m: f'(uuid "{U("mh",i,m.start())}")', body)
    # a mounting hole needs no silkscreen: the ring adds nothing a 3.2 mm hole
    # does not already say, and the REF** text just collides with neighbours
    # the only silk a MountingHole carries is an fp_text "${REFERENCE}"; the two
    # circles are Cmts.User and F.CrtYd, neither of which is printed
    body=re.sub(r'\t\(fp_text user "\$\{REFERENCE\}"\n(?:\t\t.*\n)*?\t\)\n', '', body)
    body=re.sub(r'(\(property "(?:Reference|Value)" "[^"]*"\n(?:\t\t.*\n)*?\t\t\(effects\n(?:\t\t\t.*\n)*?)(\t\t\)\n)',
                lambda m: m.group(1)+'\t\t\t(hide yes)\n'+m.group(2), body)
    return (f'\t(footprint "MountingHole:MountingHole_3.2mm_M3"\n'
            f'\t\t(layer "F.Cu")\n\t\t(uuid "{U("mh",i)}")\n\t\t(at {x+OX} {y+OY})\n'
            + body + "\t)\n")

out=[]
# outline
out += [line(0,0,W,0,tag="n"), line(W,0,W,H,tag="e"), line(W,H,0,H,tag="s"), line(0,H,0,0,tag="w")]
for i,(hx,hy) in enumerate(HOLES): out.append(mounting_hole(hx,hy,i))
# BT1 keep-out, drawn so the cell's footprint is obvious before anything is placed
bx0,bx1,by0,by1 = 35.40, 114.60, 3.55, 24.45
for a,b,c,d,t in ((bx0,by0,bx1,by0,"a"),(bx1,by0,bx1,by1,"b"),(bx1,by1,bx0,by1,"c"),(bx0,by1,bx0,by0,"d")):
    out.append(line(a,b,c,d,layer="Cmts.User",w=0.15,tag="bt"+t))
out.append(text("BT1 18650 - 21.3 mm tall, sets the enclosure stack", bx0+2, by0-2.5, size=2.0))
out.append(text("caryatid  150 x 90 mm  2 layer", 2, H+5, size=2.5))

doc=('(kicad_pcb\n\t(version 20241229)\n\t(generator "pcbnew")\n\t(generator_version "9.0")\n'
     '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n\t(paper "A3")\n'
     + LAYERS + "\n"
     '\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t\t(allow_soldermask_bridges_in_footprints no)\n'
     '\t\t(aux_axis_origin 0 0)\n\t\t(grid_origin 0 0)\n\t)\n'
     '\t(net 0 "")\n' + "".join(out) + ')\n')
tgt=os.path.join(PCB,"caryatid.kicad_pcb")
if os.path.exists(tgt) and os.path.getsize(tgt)>4000:
    sys.exit(f"refusing: {tgt} already has content")
open(tgt,"w").write(doc)
print(f"wrote {tgt}  ({len(doc)} chars)")
