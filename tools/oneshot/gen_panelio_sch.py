#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Used once to bootstrap hardware/pcb/panel-io.kicad_sch. Do not run again.

Same contract as the other generators here -- see tools/oneshot/README.md.
"""
import os, sys, uuid
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot bootstrap, would discard GUI edits to panel-io.kicad_sch")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib

PCB=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","hardware","pcb")
ROOT="49c08c53-8a29-4df2-81cf-05d7b7c47990"
SHEET="810df3d0-2a5c-411d-aa14-77e2cbf45434"
PATH=f"/{ROOT}/{SHEET}"
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS,"caryatid-panelio:"+":".join(map(str,k))))
GRID=1.27
def snap(v): return round(round(v/GRID)*GRID,2)
def r2(v): return round(v,2)
P="pwr"; L="lbl"; G="glbl"; NC="nc"
CG="Connector_Generic"; D="Device"
IDC="Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical"
XH={2:"Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
    3:"Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
    4:"Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    6:"Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical"}
SH4="Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"
R0603="Resistor_SMD:R_0603_1608Metric"; C0603="Capacitor_SMD:C_0603_1608Metric"

C=[]
def add(ref,lib,sym,val,fp,x,y,pm,unit=1,dnp=False): C.append((ref,lib,sym,val,fp,x,y,pm,unit,dnp))

# ---- J5 analogue bus: rails outboard, 1k/100nF per wiper ------------------
AW=["A0","A1","A2","A3","A6","A7","A8","A9"]
add("J5",CG,"Conn_02x05_Odd_Even","Analogue bus",IDC,60,60,
    {1:(P,"+3V3A"),10:(P,"GND"),**{i+2:(L,f"{n}_W") for i,n in enumerate(AW)}})
for i,n in enumerate(AW):
    add(f"R{19+i}",D,"R","1k",R0603, 110+ (i%4)*30, 45+(i//4)*45, {"1":(L,f"{n}_W"),"2":(G,n)})
    add(f"C{10+i}",D,"C","100n",C0603, 125+(i%4)*30, 60+(i//4)*45, {"1":(G,n),"2":(P,"GND")})

# ---- J11 digital bus: 100R series on D0-D6, pin 9 spare ------------------
add("J11",CG,"Conn_02x05_Odd_Even","Digital bus",IDC,60,175,
    {1:(P,"+3V3"),10:(P,"GND"),9:(NC,""),**{i+2:(L,f"D{i}_S") for i in range(7)}})
for i in range(7):
    add(f"R{27+i}",D,"R","100R",R0603, 110+(i%4)*30, 160+(i//4)*45, {"1":(L,f"D{i}_S"),"2":(G,f"D{i}")})

# ---- switches: RC into 74HC14 (U3), three channels ------------------------
SW=[("SW1","J6","D14",1,"1","2","220n"),("SW2","J7","D13",2,"3","4","220n"),
    ("SW3","J8","D7", 3,"5","6","1u")]
for k,(nm,jref,net,unit,pin_i,pin_o,cv) in enumerate(SW):
    y=270+k*60
    add(jref,CG,"Conn_01x02",f"{nm} switch",XH[2],50,y,{1:(L,f"{nm}_RAW"),2:(P,"GND")})
    add(f"R{34+k*2}",D,"R","10k",R0603, 85,y-25,{"1":(P,"+3V3"),"2":(L,f"{nm}_RAW")})
    add(f"R{35+k*2}",D,"R","10k",R0603, 115,y,   {"1":(L,f"{nm}_RAW"),"2":(L,f"{nm}_F")})
    add(f"C{19+k}",D,"C",cv,C0603,     145,y+18, {"1":(L,f"{nm}_F"),"2":(P,"GND")})
    add("U3","74xx","74HC14","74HC14","Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        190,y,{pin_i:(L,f"{nm}_F"),pin_o:(G,net)},unit=unit)
# unused gates: inputs to GND, outputs left open
for unit,(pi,po) in {4:("9","8"),5:("11","10"),6:("13","12")}.items():
    add("U3","74xx","74HC14","74HC14","Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        270,60+(unit-4)*45,{pi:(P,"GND"),po:(NC,"")},unit=unit)   # clear of the J11 series resistors
add("U3","74xx","74HC14","74HC14","Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    280,300,{"14":(P,"+3V3"),"7":(P,"GND")},unit=7)
add("C18",D,"C","100n",C0603,315,300,{"1":(P,"+3V3"),"2":(P,"GND")})

# ---- J12 RGB: common anode on +5V, cathodes through resistors ------------
for i,(pin,val,net,nm) in enumerate([(2,"510","D26","R"),(3,"300","D27","G"),(4,"300","D29","B")]):
    add(f"R{40+i}",D,"R",val,R0603, 400+i*28, 70, {"1":(L,f"RGB_{nm}"),"2":(G,net)})
add("J12",CG,"Conn_01x04","RGB status",XH[4],355,60,
    {1:(P,"+5V"),2:(L,"RGB_R"),3:(L,"RGB_G"),4:(L,"RGB_B")})

# ---- comms port A: Qwiic and module footprints share D11/D12 -------------
add("J13A",CG,"Conn_01x04","Comms A - Qwiic",SH4,355,150,
    {1:(P,"GND"),2:(P,"+3V3"),3:(G,"D12"),4:(G,"D11")})
add("R43",D,"R","4k7",R0603,410,140,{"1":(P,"+3V3"),"2":(G,"D12")},dnp=True)
add("R44",D,"R","4k7",R0603,440,140,{"1":(P,"+3V3"),"2":(G,"D11")},dnp=True)
add("J13B",CG,"Conn_01x06","Comms A - module",XH[6],355,215,
    {1:(P,"+5V"),2:(P,"+3V3"),3:(P,"GND"),4:(G,"D11"),5:(G,"D12"),6:(P,"GND")})
add("J15",CG,"Conn_01x06","Comms B - module",XH[6],355,285,
    {1:(P,"+5V"),2:(P,"+3V3"),3:(P,"GND"),4:(G,"D13"),5:(G,"D14"),6:(P,"GND")})

# ---- J16 expansion / SPI1 -------------------------------------------------
add("J16",CG,"Conn_02x04_Odd_Even","Expansion / SPI1","Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
    505,60,{1:(P,"+5V"),2:(P,"+3V3"),3:(P,"GND"),4:(P,"GND"),
            5:(G,"D8"),6:(G,"D9"),7:(G,"D10"),8:(G,"D30")})

# ---- sensors: pulldowns are DNP options; A4=10k FSR, A5=3k soft pot ------
add("J9",CG,"Conn_01x03","Soft pot",XH[3],470,160,{1:(P,"+3V3A"),2:(G,"A5"),3:(P,"GND")})
add("R45",D,"R","3k",R0603,520,165,{"1":(G,"A5"),"2":(P,"GND")},dnp=True)
add("J10",CG,"Conn_01x02","FSR",XH[2],470,230,{1:(P,"+3V3A"),2:(G,"A4")})
add("R46",D,"R","10k",R0603,520,230,{"1":(G,"A4"),"2":(P,"GND")},dnp=True)

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
tgt=os.path.join(PCB,"panel-io.kicad_sch")
old=open(tgt).read()
head=old[:old.index("\t(lib_symbols")].replace('(paper "A4")','(paper "A2")')
open(tgt,"w").write(head+"\t(lib_symbols\n"+libs+"\n\t)\n"+"".join(out)+
  '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "4")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
print(f"placements={len(C)}  lib_symbols={len(used)}")
