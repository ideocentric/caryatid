#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Used once to bootstrap hardware/pcb/seed.kicad_sch. Do not run again.

Same contract as gen_power_sch.py -- see tools/oneshot/README.md. The schematic
is the artefact now; re-running this discards every GUI edit.
"""
import os, sys, re, uuid
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot bootstrap, would discard GUI edits to seed.kicad_sch")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib

PCB=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hardware", "pcb")
ROOT="49c08c53-8a29-4df2-81cf-05d7b7c47990"
SHEET="ec282f9b-b5a6-47a8-bf01-1f498ec00137"
PATH=f"/{ROOT}/{SHEET}"
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS, "caryatid-seed:"+":".join(map(str,k))))
GRID=1.27
def snap(v): return round(round(v/GRID)*GRID, 2)
def r2(v): return round(v, 2)
P="pwr"; L="lbl"; G="glbl"

# Seed pins leave as a GLOBAL label named for the pin -- unqualified, so the
# A? / A?? / AUDIO_* netclass patterns match. A local label would become
# /seed/A7 and silently miss.
A1={n:(G,f"D{n-1}") for n in range(1,16)}
A1.update({16:(G,"AUDIO_IN_L"),17:(G,"AUDIO_IN_R"),18:(G,"AUDIO_OUT_L"),19:(G,"AUDIO_OUT_R"),
           20:(P,"GND")})
A2={21:(P,"+3V3A"),38:(P,"+3V3"),39:(P,"+5V"),40:(P,"GND"),32:(G,"A10"),35:(G,"A11"),
    33:(G,"D26"),34:(G,"D27"),36:(G,"D29"),37:(G,"D30")}
A2.update({n:(G,f"A{n-22}") for n in range(22,32)})

C=[
 ("A1","caryatid","Daisy_Seed_Socket_A","1x20 socket","caryatid:DaisySeed_Socket_A_1x20",100,100,A1),
 ("A2","caryatid","Daisy_Seed_Socket_B","1x20 socket","caryatid:DaisySeed_Socket_B_1x20",100,100,A2),
 # battery gauge -- A10
 ("R11","Device","R","100k","Resistor_SMD:R_0603_1608Metric",190,70,{"1":(P,"VBAT"),"2":(L,"A10_DIV")}),
 ("R12","Device","R","100k","Resistor_SMD:R_0603_1608Metric",190,95,{"1":(L,"A10_DIV"),"2":(P,"GND")}),
 ("R13","Device","R","1k","Resistor_SMD:R_0603_1608Metric",215,82,{"1":(L,"A10_DIV"),"2":(G,"A10")}),
 ("C8","Device","C","10n","Capacitor_SMD:C_0603_1608Metric",240,95,{"1":(G,"A10"),"2":(P,"GND")}),
 # charge-status code -- A11
 ("R14","Device","R","10k 0.1%","Resistor_SMD:R_0603_1608Metric",190,160,{"1":(P,"+3V3"),"2":(L,"A11_DIV")}),
 ("R15","Device","R","10k 0.1%","Resistor_SMD:R_0603_1608Metric",190,190,{"1":(L,"A11_DIV"),"2":(G,"~{CHG}")}),
 ("R16","Device","R","10k 0.1%","Resistor_SMD:R_0603_1608Metric",215,190,{"1":(L,"A11_DIV"),"2":(L,"PGOOD_LEG")}),
 ("R17","Device","R","10k 0.1%","Resistor_SMD:R_0603_1608Metric",215,215,{"1":(L,"PGOOD_LEG"),"2":(G,"~{PGOOD}")}),
 ("R18","Device","R","1k","Resistor_SMD:R_0603_1608Metric",245,172,{"1":(L,"A11_DIV"),"2":(G,"A11")}),
 ("C9","Device","C","10n","Capacitor_SMD:C_0603_1608Metric",270,185,{"1":(G,"A11"),"2":(P,"GND")}),
]
LOCAL_RAILS={"VBAT","VOUT","VIN_DC","+5V_RAW","+3V3A"}

def prop(k,v,x,y,hide=False):
    h='\n\t\t\t\t(hide yes)' if hide else ''
    return (f'\t\t(property "{k}" "{v}"\n\t\t\t(at {x} {y} 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){h}\n\t\t\t)\n\t\t)\n')

out=[]; used={}
for ref,lib,sym,val,fp,x,y,pinmap in C:
    x,y = snap(x), snap(y)
    ldx = -19 if ref=="A1" else 6
    used[(lib,sym)]=True
    ps={p[0]:p for p in symlib.pins_resolved(lib,sym)}
    s=(f'\t(symbol\n\t\t(lib_id "{lib}:{sym}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
       '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
       # A1 and A2 share an origin, so their labels must go to opposite sides
       f'\t\t(uuid "{U(ref)}")\n' + prop("Reference",ref,x+ldx,y-30) + prop("Value",val,x+ldx,y-27)
       + prop("Footprint",fp,x,y,True) + prop("Datasheet","~",x,y,True) + prop("Description","",x,y,True))
    for pn in sorted(ps,key=lambda n:int(n)):
        s+=f'\t\t(pin "{pn}"\n\t\t\t(uuid "{U(ref,pn)}")\n\t\t)\n'
    s+=(f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
    out.append(s)
    for pn,(kind,name) in pinmap.items():
        pn=str(pn)
        if pn not in ps: raise KeyError(f"{ref}: no pin {pn}")
        _,sx,sy,ang,_=ps[pn]
        px,py = r2(x+sx), r2(y-sy)
        STUB=5.08
        dx,dy={0:(-STUB,0),90:(0,STUB),180:(STUB,0),270:(0,-STUB)}[ang%360]
        ex,ey=r2(px+dx), r2(py+dy)
        out.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {px} {py}) (xy {ex} {ey})\n\t\t)\n'
                   f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U(ref,pn,"w")}")\n\t)\n')
        px,py=ex,ey
        la={0:180,90:270,180:0,270:90}[ang%360]
        if kind==P:
            plib="caryatid" if name in LOCAL_RAILS else "power"
            used[(plib,name)]=True
            out.append(f'\t(symbol\n\t\t(lib_id "{plib}:{name}")\n\t\t(at {px} {py} {la})\n\t\t(unit 1)\n'
                       '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                       f'\t\t(uuid "{U(ref,pn,"p")}")\n' + prop("Reference","#PWR",px,py,True)
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

libs="\n".join(symlib.flat_entry(l,s) for (l,s) in sorted(used))
tgt=os.path.join(PCB,"seed.kicad_sch")
old=open(tgt).read()
head=old[:old.index("\t(lib_symbols")].replace('(paper "A4")','(paper "A3")')
open(tgt,"w").write(head + "\t(lib_symbols\n" + libs + "\n\t)\n" + "".join(out) +
    '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "2")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
print(f"components={len(C)}  lib_symbols={len(used)}")
