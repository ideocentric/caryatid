#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Used once to bootstrap hardware/pcb/audio.kicad_sch. Do not run again.

Same contract as the other generators here -- see tools/oneshot/README.md.

Every input-side part is DNP. The capsule has not been measured, and audio.md
lays out carbon / electret / dynamic so the choice becomes a population decision
after the boards arrive rather than a gate before the gerbers go out.
"""
import os, sys, uuid
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot bootstrap, would discard GUI edits to audio.kicad_sch")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib

PCB=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","hardware","pcb")
ROOT="49c08c53-8a29-4df2-81cf-05d7b7c47990"
SHEET="bda31c7d-e5ef-4a38-8900-64d829b923ab"
PATH=f"/{ROOT}/{SHEET}"
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS,"caryatid-audio:"+":".join(map(str,k))))
GRID=1.27
def snap(v): return round(round(v/GRID)*GRID,2)
def r2(v): return round(v,2)
P="pwr"; L="lbl"; G="glbl"; NC="nc"
CG="Connector_Generic"; D="Device"
R0603="Resistor_SMD:R_0603_1608Metric"; C0603="Capacitor_SMD:C_0603_1608Metric"
C0805="Capacitor_SMD:C_0805_2012Metric"
XH3="Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"
XH2="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"

C=[]
def add(ref,lib,sym,val,fp,x,y,pm,unit=1,dnp=False): C.append((ref,lib,sym,val,fp,x,y,pm,unit,dnp))

# ============ OUTPUT -- the only block populated on every build ============
# Seed AUDIO OUT through a series resistor. Laid out as a divider so either arm
# can become a link: a telephone earpiece wants attenuation, headphones do not.
add("J17",CG,"Conn_01x03","Audio out L/R/G",XH3,60,60,
    {1:(L,"OUT_L_J"),2:(L,"OUT_R_J"),3:(P,"GND")})
add("R47",D,"R","1k",R0603,110,45,{"1":(G,"AUDIO_OUT_L"),"2":(L,"OUT_L_J")})
add("R48",D,"R","open",R0603,140,55,{"1":(L,"OUT_L_J"),"2":(P,"GND")},dnp=True)
add("R49",D,"R","1k",R0603,110,95,{"1":(G,"AUDIO_OUT_R"),"2":(L,"OUT_R_J")})
add("R50",D,"R","open",R0603,140,105,{"1":(L,"OUT_R_J"),"2":(P,"GND")},dnp=True)

# ============ INPUT -- everything below is DNP ==============================
# J18 carries both capsule leads. The RETURN goes out on J14 so the hook
# switch's second pole can break the bias current in copper; link J14 for
# always-on. See audio.md.
add("J18",CG,"Conn_01x03","Audio in L/R/rtn",XH3,60,180,
    {1:(L,"MIC_L"),2:(L,"MIC_R"),3:(L,"MIC_RTN")})
add("J14",CG,"Conn_01x02","Mic bias return",XH2,60,240,
    {1:(L,"MIC_RTN"),2:(P,"GND")})

for ch,(x0,y0) in {"L":(0,0),"R":(0,150)}.items():   # 150 keeps the R block inside A2
    BX,BY=150+x0, 170+y0
    # capsule bias -- populate exactly one, or neither for a line source
    add(f"R{51 if ch=='L' else 53}",D,"R","2k2",R0603,BX-40,BY-40,
        {"1":(P,"+3V3A"),"2":(L,f"MIC_{ch}")},dnp=True)          # electret
    add(f"R{52 if ch=='L' else 54}",D,"R","220R",R0603,BX-10,BY-40,
        {"1":(P,"+5V"),"2":(L,f"MIC_{ch}")},dnp=True)            # carbon, size on the bench
    # mid-rail reference, one per channel so the two + inputs are not shorted
    b1,b2 = (55,56) if ch=="L" else (59,60)
    cb    = 22 if ch=="L" else 26
    add(f"R{b1}",D,"R","100k",R0603,BX+30,BY-30,{"1":(P,"+3V3A"),"2":(L,f"VBIAS_{ch}")},dnp=True)
    add(f"R{b2}",D,"R","100k",R0603,BX+30,BY+10,{"1":(L,f"VBIAS_{ch}"),"2":(P,"GND")},dnp=True)
    add(f"C{cb}",D,"C","10u",C0805,BX+60,BY+10,{"1":(L,f"VBIAS_{ch}"),"2":(P,"GND")},dnp=True)
    # signal in: C_in couples onto the biased + input
    cin = 23 if ch=="L" else 27
    add(f"C{cin}",D,"C","1u",C0603,BX,BY-15,{"1":(L,f"MIC_{ch}"),"2":(L,f"VBIAS_{ch}")},dnp=True)
    # gain: Rf/Rg set AC gain, C_g in series with Rg makes DC gain exactly 1
    rf,rg = (57,58) if ch=="L" else (61,62)
    cg    = 24 if ch=="L" else 28
    add(f"R{rf}",D,"R","100k",R0603,BX+100,BY-35,{"1":(L,f"OPA_{ch}_N"),"2":(L,f"OPA_{ch}_O")},dnp=True)
    add(f"R{rg}",D,"R","1k",R0603,BX+70,BY+45,{"1":(L,f"OPA_{ch}_N"),"2":(L,f"GAINLEG_{ch}")},dnp=True)
    add(f"C{cg}",D,"C","10u",C0805,BX+70,BY+75,{"1":(L,f"GAINLEG_{ch}"),"2":(P,"GND")},dnp=True)
    # op-amp unit
    unit = 1 if ch=="L" else 2
    pins = {"3":(L,f"VBIAS_{ch}"),"2":(L,f"OPA_{ch}_N"),"1":(L,f"OPA_{ch}_O")} if ch=="L" \
      else {"5":(L,f"VBIAS_{ch}"),"6":(L,f"OPA_{ch}_N"),"7":(L,f"OPA_{ch}_O")}
    add("U4","caryatid","MCP6002","MCP6002","Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        BX+130,BY,pins,unit=unit,dnp=True)
    # C_out strips the mid-rail pedestal back off before the codec
    cout = 25 if ch=="L" else 29
    add(f"C{cout}",D,"C","10u",C0805,BX+175,BY,{"1":(L,f"OPA_{ch}_O"),"2":(G,f"AUDIO_IN_{ch}")},dnp=True)
    # bypass, laid out as a divider: 0R alone is a straight pass, both arms a pad
    rs,rsh = (63,64) if ch=="L" else (65,66)
    add(f"R{rs}",D,"R","0R",R0603,BX+250,BY+40,{"1":(L,f"MIC_{ch}"),"2":(G,f"AUDIO_IN_{ch}")},dnp=True)
    add(f"R{rsh}",D,"R","open",R0603,BX+290,BY+40,{"1":(G,f"AUDIO_IN_{ch}"),"2":(P,"GND")},dnp=True)

add("U4","caryatid","MCP6002","MCP6002","Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    100,340,{"8":(P,"+3V3A"),"4":(P,"GND")},unit=3,dnp=True)
add("C30",D,"C","100n",C0603,140,340,{"1":(P,"+3V3A"),"2":(P,"GND")},dnp=True)

LOCAL_RAILS={"VBAT","VOUT","VIN_DC","+5V_RAW","+3V3A"}
def prop(k,v,x,y,hide=False):
    h='\n\t\t\t\t(hide yes)' if hide else ''
    return (f'\t\t(property "{k}" "{v}"\n\t\t\t(at {x} {y} 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){h}\n\t\t\t)\n\t\t)\n')

out=[]; used={}
for ref,lib,sym,val,fp,x,y,pinmap,unit,dnp in C:
    x,y=snap(x),snap(y); used[(lib,sym)]=True
    allp={p[0]:p for p in symlib.pins_unit(lib,sym,unit)} or {p[0]:p for p in symlib.pins_resolved(lib,sym)}
    s=(f'\t(symbol\n\t\t(lib_id "{lib}:{sym}")\n\t\t(at {x} {y} 0)\n\t\t(unit {unit})\n'
       '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
       f'\t\t(dnp {"yes" if dnp else "no"})\n\t\t(uuid "{U(ref,unit)}")\n'
       + prop("Reference",ref,x+6,y-12) + prop("Value",val,x+6,y-9)
       + prop("Footprint",fp,x,y,True) + prop("Datasheet","~",x,y,True) + prop("Description","",x,y,True))
    for pn in sorted(allp,key=lambda n:int(n)):
        s+=f'\t\t(pin "{pn}"\n\t\t\t(uuid "{U(ref,unit,pn)}")\n\t\t)\n'
    s+=(f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
    out.append(s)
    for pn,(kind,name) in pinmap.items():
        pn=str(pn)
        if pn not in allp: raise KeyError(f"{ref} unit {unit}: no pin {pn}")
        _,sx,sy,ang,_=allp[pn]
        px,py=r2(x+sx),r2(y-sy); STUB=5.08
        dx,dy={0:(-STUB,0),90:(0,STUB),180:(STUB,0),270:(0,-STUB)}[ang%360]
        ex,ey=r2(px+dx),r2(py+dy)
        if kind!=NC:
            out.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {px} {py}) (xy {ex} {ey})\n\t\t)\n'
                       f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U(ref,unit,pn,"w")}")\n\t)\n')
            px,py=ex,ey
        la={0:180,90:270,180:0,270:90}[ang%360]
        if kind==P:
            plib="caryatid" if name in LOCAL_RAILS else "power"; used[(plib,name)]=True
            out.append(f'\t(symbol\n\t\t(lib_id "{plib}:{name}")\n\t\t(at {px} {py} {la})\n\t\t(unit 1)\n'
                       '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                       f'\t\t(uuid "{U(ref,unit,pn,"p")}")\n' + prop("Reference","#PWR",px,py,True)
                       + prop("Value",name,px,py+3)
                       + f'\t\t(pin "1"\n\t\t\t(uuid "{U(ref,unit,pn,"pp")}")\n\t\t)\n'
                       + f'\t\t(instances\n\t\t\t(project "caryatid"\n\t\t\t\t(path "{PATH}"\n'
                         f'\t\t\t\t\t(reference "#PWR?")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
        elif kind==L:
            out.append(f'\t(label "{name}"\n\t\t(at {px} {py} {la})\n\t\t(effects\n\t\t\t(font\n'
                       f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n'
                       f'\t\t(uuid "{U(ref,unit,pn,"l")}")\n\t)\n')
        elif kind==G:
            out.append(f'\t(global_label "{name}"\n\t\t(shape bidirectional)\n\t\t(at {px} {py} {la})\n'
                       f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n'
                       f'\t\t(uuid "{U(ref,unit,pn,"g")}")\n\t)\n')
        elif kind==NC:
            out.append(f'\t(no_connect\n\t\t(at {px} {py})\n\t\t(uuid "{U(ref,unit,pn,"nc")}")\n\t)\n')

libs="\n".join(symlib.flat_entry(l,s) for (l,s) in sorted(used))
tgt=os.path.join(PCB,"audio.kicad_sch")
old=open(tgt).read()
head=old[:old.index("\t(lib_symbols")].replace('(paper "A4")','(paper "A2")')
open(tgt,"w").write(head+"\t(lib_symbols\n"+libs+"\n\t)\n"+"".join(out)+
  '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "3")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
print(f"placements={len(C)}  lib_symbols={len(used)}  dnp={sum(1 for c in C if c[9])}")
