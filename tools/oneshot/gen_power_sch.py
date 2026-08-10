#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Used once to bootstrap hardware/pcb/power.kicad_sch. Do not run again.

The schematic is now the artefact and is edited in KiCad. Re-running this
regenerates it from the component table below and DISCARDS every GUI edit --
placement, wiring, anything added since. That is the whole hazard: this file
looks like a generator but the thing it generates is no longer derived.

Kept for provenance: it records exactly how the first capture was produced, and
why the netlist could be diffed against docs/power-sheet.md node by node.

If the circuit changes, change the schematic in KiCad and update
docs/power-sheet.md. Do not come back here.

    CARYATID_ALLOW_REGEN=1 python3 tools/oneshot/gen_power_sch.py

is deliberately awkward, and still destructive.
"""
import os, sys
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: this is a one-shot bootstrap and would discard "
             "GUI edits to power.kicad_sch. See the docstring.")

import re, uuid, symlib

ROOT="49c08c53-8a29-4df2-81cf-05d7b7c47990"
SHEET="2a268859-e48a-4840-9d32-9349703f095d"
PATH=f"/{ROOT}/{SHEET}"
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS, "caryatid-power:"+":".join(map(str,k))))

P="pwr"; L="lbl"; G="glbl"; NC="nc"

# ref, lib, sym, value, footprint, x, y, {pin: (kind, name)}
C=[
 ("J1","Connector_Generic","Conn_01x02","DC in","Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
   40,60,{"1":(L,"DC_IN"),"2":(P,"GND")}),
 ("D1","Device","D_Schottky","SS34","Diode_SMD:D_SMA",
   70,60,{"2":(L,"DC_IN"),"1":(P,"VIN_DC")}),
 ("C1","Device","C","10u/25V","Capacitor_SMD:C_0805_2012Metric",
   95,68,{"1":(P,"VIN_DC"),"2":(P,"GND")}),
 ("U1","caryatid","BQ24074RGT","BQ24074RGT","caryatid:BQ24074RGT_QFN-16-1EP_3x3mm_P0.5mm",
   150,72,{"13":(P,"VIN_DC"),"8":(P,"GND"),"17":(P,"GND"),
           "2":(P,"VBAT"),"3":(P,"VBAT"),"10":(P,"VOUT"),"11":(P,"VOUT"),
           "1":(L,"TS"),"4":(P,"GND"),"6":(P,"GND"),"5":(P,"VOUT"),
           "12":(L,"ILIM"),"16":(L,"ISET"),"14":(L,"TMR"),"15":(NC,""),
           "7":(G,"~{PGOOD}"),"9":(G,"~{CHG}")}),
 ("R1","Device","R","10k","Resistor_SMD:R_0603_1608Metric",115,120,{"1":(L,"TS"),"2":(P,"GND")}),
 ("R2","Device","R","1k2","Resistor_SMD:R_0603_1608Metric",135,120,{"1":(L,"ILIM"),"2":(P,"GND")}),
 ("R3","Device","R","887R 1%","Resistor_SMD:R_0603_1608Metric",155,120,{"1":(L,"ISET"),"2":(P,"GND")}),
 ("R4","Device","R","46k4","Resistor_SMD:R_0603_1608Metric",175,120,{"1":(L,"TMR"),"2":(P,"GND")}),
 ("BT1","Device","Battery_Cell","18650 protected","Battery:BatteryHolder_MPD_BH-18650-PC",
   225,62,{"1":(P,"VBAT"),"2":(P,"GND")}),
 ("J2","Connector_Generic","Conn_01x02","Battery, remote","Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
   250,62,{"1":(P,"VBAT"),"2":(P,"GND")}),
 ("C2","Device","C","10u","Capacitor_SMD:C_0805_2012Metric",275,68,{"1":(P,"VBAT"),"2":(P,"GND")}),
 ("C3","Device","C","10u","Capacitor_SMD:C_0805_2012Metric",295,68,{"1":(P,"VOUT"),"2":(P,"GND")}),
 ("J3","Connector_Generic","Conn_01x04","Latch switch","Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
   40,170,{"1":(P,"VOUT"),"2":(L,"EN_SW"),"3":(L,"LAMP"),"4":(P,"GND")}),
 ("R5","Device","R","0R","Resistor_SMD:R_0603_1608Metric",70,163,{"1":(P,"+5V"),"2":(L,"LAMP")}),
 ("R6","Device","R","100k","Resistor_SMD:R_0603_1608Metric",90,180,{"1":(L,"EN_SW"),"2":(P,"GND")}),
 ("U2","caryatid","TPS61023DRL","TPS61023DRL","Package_TO_SOT_SMD:SOT-563",
   160,175,{"1":(L,"FB"),"2":(L,"EN_SW"),"3":(P,"VOUT"),"4":(P,"GND"),"5":(L,"SW"),"6":(P,"+5V_RAW")}),
 ("L1","Device","L","1uH 4.2A","Inductor_SMD:L_Vishay_IFSC-1515AH_4x4x1.8mm",
   130,150,{"1":(P,"VOUT"),"2":(L,"SW")}),
 ("C4","Device","C","10u","Capacitor_SMD:C_0805_2012Metric",120,205,{"1":(P,"VOUT"),"2":(P,"GND")}),
 ("C5","Device","C","10u","Capacitor_SMD:C_0805_2012Metric",140,205,{"1":(P,"VOUT"),"2":(P,"GND")}),
 ("C6","Device","C","22u","Capacitor_SMD:C_0805_2012Metric",210,205,{"1":(P,"+5V_RAW"),"2":(P,"GND")}),
 ("R7","Device","R","348k 1%","Resistor_SMD:R_0603_1608Metric",235,170,{"1":(P,"+5V_RAW"),"2":(L,"FB")}),
 ("R8","Device","R","47k5 1%","Resistor_SMD:R_0603_1608Metric",235,195,{"1":(L,"FB"),"2":(P,"GND")}),
 ("FB1","Device","FerriteBead","FB >=1A","Inductor_SMD:L_0805_2012Metric",
   275,150,{"1":(P,"+5V_RAW"),"2":(P,"+5V")}),
 ("C7","Device","C_Polarized","100u","Capacitor_SMD:CP_Elec_6.3x5.4",300,160,{"1":(P,"+5V"),"2":(P,"GND")}),
 ("J4","Connector_Generic","Conn_01x04","Charge LEDs","Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
   330,240,{"1":(P,"VOUT"),"2":(L,"CHG_LED"),"3":(L,"PGOOD_LED"),"4":(P,"GND")}),
 ("R9","Device","R","1k","Resistor_SMD:R_0603_1608Metric",360,232,{"1":(L,"CHG_LED"),"2":(G,"~{CHG}")}),
 ("R10","Device","R","1k","Resistor_SMD:R_0603_1608Metric",385,232,{"1":(L,"PGOOD_LED"),"2":(G,"~{PGOOD}")}),
]
# nets whose only pins are sinks/passive -> ERC needs an explicit source flag
FLAGS=[("GND",40,275),("VIN_DC",70,275),("VBAT",100,275),("+5V",130,275)]

GRID=1.27
def snap(v): return round(round(v/GRID)*GRID, 2)
def r2(v):   return round(v, 2)

def prop(k,v,x,y,hide=False,just=None):
    e=f'\n\t\t\t\t(justify {just})' if just else ''
    h='\n\t\t\t\t(hide yes)' if hide else ''
    return (f'\t\t(property "{k}" "{v}"\n\t\t\t(at {x} {y} 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){e}{h}\n\t\t\t)\n\t\t)\n')

out=[]; used={}
for ref,lib,sym,val,fp,x,y,pinmap in C:
    x,y = snap(x), snap(y)
    used[(lib,sym)]=True
    ps={p[0]:p for p in symlib.pins_resolved(lib,sym)}
    s=f'\t(symbol\n\t\t(lib_id "{lib}:{sym}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
    s+='\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
    s+=f'\t\t(uuid "{U(ref)}")\n'
    s+=prop("Reference",ref,x+6,y-6)
    s+=prop("Value",val,x+6,y-3)
    s+=prop("Footprint",fp,x,y,hide=True)
    s+=prop("Datasheet","~",x,y,hide=True)
    s+=prop("Description","",x,y,hide=True)
    for pn in sorted(ps,key=lambda n:int(n) if n.isdigit() else 0):
        s+=f'\t\t(pin "{pn}"\n\t\t\t(uuid "{U(ref,pn)}")\n\t\t)\n'
    s+=(f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
    out.append(s)
    for pn,(kind,name) in pinmap.items():
        if pn not in ps: raise KeyError(f"{ref}: no pin {pn} on {lib}:{sym}")
        _,sx,sy,ang,_=ps[pn]
        px,py = r2(x+sx), r2(y-sy)
        # stub outward from the body so the label/rail does not sit on top of the symbol
        STUB=5.08
        dx,dy = {0:(-STUB,0), 90:(0,STUB), 180:(STUB,0), 270:(0,-STUB)}[ang%360]
        ex,ey = r2(px+dx), r2(py+dy)
        out.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {px} {py}) (xy {ex} {ey})\n\t\t)\n'
                   f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
                   f'\t\t(uuid "{U(ref,pn,"w")}")\n\t)\n')
        px,py = ex,ey
        la={0:180, 90:270, 180:0, 270:90}[ang%360]
        if kind==P:
            plib="caryatid" if name in ("VBAT","VOUT","VIN_DC","+5V_RAW") else "power"
            used[(plib,name)]=True
            out.append(f'\t(symbol\n\t\t(lib_id "{plib}:{name}")\n\t\t(at {px} {py} {la})\n\t\t(unit 1)\n'
                       f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                       f'\t\t(uuid "{U(ref,pn,"p")}")\n'
                       + prop("Reference","#PWR",px,py,hide=True)
                       + prop("Value",name,px,py+3)
                       + f'\t\t(pin "1"\n\t\t\t(uuid "{U(ref,pn,"pp")}")\n\t\t)\n'
                       + f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
                         f'\t\t\t\t\t(reference "#PWR?")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
        elif kind==L:
            out.append(f'\t(label "{name}"\n\t\t(at {px} {py} {la})\n\t\t(effects\n\t\t\t(font\n'
                       f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n'
                       f'\t\t(uuid "{U(ref,pn,"l")}")\n\t)\n')
        elif kind==G:
            out.append(f'\t(global_label "{name}"\n\t\t(shape bidirectional)\n\t\t(at {px} {py} {la})\n'
                       f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n'
                       f'\t\t(uuid "{U(ref,pn,"g")}")\n\t)\n')
        elif kind==NC:
            out.pop()  # remove the stub wire; a no-connect belongs on the pin itself
            out.append(f'\t(no_connect\n\t\t(at {r2(x+sx)} {r2(y-sy)})\n\t\t(uuid "{U(ref,pn,"nc")}")\n\t)\n')

for name,x,y in FLAGS:
    x,y = snap(x), snap(y)
    plib="caryatid" if name in ("VBAT","VOUT","VIN_DC","+5V_RAW") else "power"
    used[(plib,name)]=True; used[("power","PWR_FLAG")]=True
    for lid,r,tag in ((f"{plib}:{name}","#PWR","r"),("power:PWR_FLAG","#FLG","f")):
        out.append(f'\t(symbol\n\t\t(lib_id "{lid}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
                   f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                   f'\t\t(uuid "{U("flag",name,tag)}")\n'
                   + prop("Reference",r,x,y,hide=True)
                   + prop("Value",name if tag=="r" else "PWR_FLAG",x,y-3)
                   + f'\t\t(pin "1"\n\t\t\t(uuid "{U("flag",name,tag,"p")}")\n\t\t)\n'
                   + f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
                     f'\t\t\t\t\t(reference "{r}?")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')

libs="\n".join(symlib.flat_entry(l,s) for (l,s) in sorted(used))
old=open("/Users/matt/Documents/GitHub/personal/caryatid/hardware/pcb/power.kicad_sch").read()
head=old[:old.index("\t(lib_symbols")]   # idempotent: matches empty or populated
head=head.replace('(paper "A4")','(paper "A3")')
doc=head + "\t(lib_symbols\n" + libs + "\n\t)\n" + "".join(out) + \
    '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n'
open("/Users/matt/Documents/GitHub/personal/caryatid/hardware/pcb/power.kicad_sch","w").write(doc)
print(f"components={len(C)}  lib_symbols={len(used)}  chars={len(doc)}")
