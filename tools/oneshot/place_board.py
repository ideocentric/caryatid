#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Placed the 125 footprints into hardware/pcb/caryatid.kicad_pcb.

kicad-cli has no "update PCB from schematic", so this does that job once: it
reads the exported netlist, embeds each footprint with its pads bound to the
right nets, and drops it into a zone. Zoning follows "Layout, when it comes" in
docs/capture-checklist.md -- switcher hard left, analogue and audio hard right.

Placement is a shelf-pack by real courtyard size, not hand-art. It is a starting
arrangement to drag from, and it is NOT routed.

Do not run again: it rewrites the board and would discard routing and any hand
placement.
"""
import os, sys, re, uuid, subprocess
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot, would discard routing and hand placement")
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
PCB=os.path.join(HERE,"..","..","hardware","pcb")
KFP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS,"caryatid-place:"+":".join(map(str,k))))
OX,OY=50.0,30.0
GRID=0.5
def sn(v): return round(round(v/GRID)*GRID,2)

NET=os.path.join(PCB,"..","..","/tmp/final.net")
net_txt=open("/tmp/final.net").read()

comps={}
for m in re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\n\s*\(value "([^"]*)"\)\s*\n\s*\(footprint "([^"]+)"\)', net_txt):
    comps[m.group(1)]=(m.group(2), m.group(3))
nets=[]; padnet={}
for b in re.split(r'\n    \(net ', net_txt[net_txt.index("  (nets"):])[1:]:
    name=re.search(r'\(name "([^"]+)"\)', b).group(1)
    code=len(nets)+1; nets.append(name)
    for r,p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', b):
        padnet[(r,p)]=(code,name)

# DNP comes from the schematics, not the netlist
dnp=set()
for f in ("power","seed","audio","panel-io"):
    s=open(os.path.join(PCB,f+".kicad_sch")).read()
    for m in re.finditer(r'\(symbol\n\t\t\(lib_id "[^"]+"\)(?:.|\n)*?\(instances', s):
        blk=m.group(0)
        if re.search(r'\(dnp yes\)', blk):
            r=re.search(r'\(property "Reference" "([^"]+)"', blk)
            if r and not r.group(1).startswith("#"): dnp.add(r.group(1))

_fpcache={}
def load_fp(libid):
    if libid in _fpcache: return _fpcache[libid]
    lib,name=libid.split(":",1)
    base=os.path.join(PCB,"caryatid.pretty") if lib=="caryatid" else os.path.join(KFP,lib+".pretty")
    t=open(os.path.join(base,name+".kicad_mod")).read()
    _fpcache[libid]=t
    return t

def bbox(libid):
    t=load_fp(libid); xs=[];ys=[]
    for chunk in re.split(r'\(fp_line|\(fp_poly|\(fp_rect|\(fp_circle|\(fp_arc', t)[1:]:
        h=chunk[:400]
        if '"F.CrtYd"' in h or '"B.CrtYd"' in h:
            for mm in re.finditer(r'\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)', h):
                xs.append(float(mm.group(1))); ys.append(float(mm.group(2)))
    if not xs:
        for mm in re.finditer(r'\(pad "[^"]*"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)', t):
            xs.append(float(mm.group(1))); ys.append(float(mm.group(2)))
    if not xs: return (3.0,3.0,0.0,0.0)
    return (max(xs)-min(xs), max(ys)-min(ys), (max(xs)+min(xs))/2, (max(ys)+min(ys))/2)

ZONES={  # x0,y0,x1,y1 -- board coords, tiling the area BT1 and the Seed leave
 "digbus":  (1,26,33,45),     # left, near A1 (digital row)
 "charger": (1,46,33,64),
 "boost":   (1,65,33,88),     # switcher hard left, away from analogue and audio
 "conn":    (35,82,99,89),    # bottom strip -- edge connectors want the edge anyway
 "seedsup": (35,26,58,40),    # A10 / A11 networks
 "anabus":  (61,26,99,48),    # analogue bus by the Seed's analogue row
 "audio":   (61,50,99,80),    # furthest point from L1
 "switch":  (35,41,58,52),
}
ZONE_OF={}
def zone(z,*refs):
    for r in refs: ZONE_OF[r]=z
zone("charger","J1","D1","C1","U1","R1","R2","R3","R4","C2","C3","J2")
zone("boost","U2","L1","C4","C5","C6","R7","R8","FB1","C7","J3","R5","R6","J4","R9","R10")
zone("seedsup","R11","R12","R13","C8","R14","R15","R16","R17","R18","C9")
zone("anabus","J5",*[f"R{n}" for n in range(19,27)],*[f"C{n}" for n in range(10,18)])
zone("digbus","J11",*[f"R{n}" for n in range(27,34)])
zone("switch","U3","J6","J7","J8",*[f"R{n}" for n in range(34,40)],"C18","C19","C20","C21")
zone("audio","J17","J18","J14","U4",*[f"R{n}" for n in range(47,67)],*[f"C{n}" for n in range(22,31)])
zone("conn","J12","R40","R41","R42","J13A","R43","R44","J13B","J15","J16","J9","R45","J10","R46")

ANCHOR={"BT1":(13.55,14.0,0),"A1":(38.0,29.0,0),"A2":(53.24,29.0,0)}

def shelf(zname, refs):
    x0,y0,x1,y1=ZONES[zname]
    items=sorted(refs, key=lambda r:-bbox(comps[r][1])[1])
    out={}; over=[]; cx,cy,rowh=x0,y0,0.0
    for r in items:
        w,h,mx,my=bbox(comps[r][1]); w+=0.6; h+=0.6
        if cx+w>x1:
            cx=x0; cy+=rowh+0.8; rowh=0.0
        if cy+h>y1: over.append(r)
        out[r]=(sn(cx+w/2-mx), sn(cy+h/2-my), 0)
        cx+=w; rowh=max(rowh,h)
    if over: print(f'  zone {zname}: {len(over)} parts past its bottom edge -> {over}')
    return out

place=dict(ANCHOR)
for z in ZONES:
    refs=[r for r,zz in ZONE_OF.items() if zz==z and r in comps and r not in place]
    place.update(shelf(z,refs))
missing=[r for r in comps if r not in place]
if missing: sys.exit(f"unplaced: {missing}")

# --- rescue pass -------------------------------------------------------
# Rectangular zones cannot express a connector ring, so some parts land off the
# board. Sweep a grid for the first slot whose courtyard clears everything
# already down, and BT1's strip, and move them there. Zone purity loses to
# being on the board.
BT=(11.15,3.55,88.85,24.45)
def rect(r):
    w,h,mx,my=bbox(comps[r][1]); x,y,_=place[r]
    return (x+mx-w/2-0.3, y+my-h/2-0.3, x+mx+w/2+0.3, y+my+h/2+0.3)
def hits(a,b): return not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])
placed_rects=[]
order=sorted(place, key=lambda r: 0 if r in ANCHOR else 1)
for r in order:
    x,y,_=place[r]
    if 0<=x<=100 and 0<=y<=90: placed_rects.append(rect(r))
rescued=[]
for r in list(place):
    x,y,_=place[r]
    if 0<=x<=100 and 0<=y<=90: continue
    w,h,mx,my=bbox(comps[r][1])
    found=None
    yy=26.0
    while yy < 90-h and not found:
        xx=1.0
        while xx < 100-w and not found:
            cand=(xx-0.3, yy-0.3, xx+w+0.3, yy+h+0.3)
            if not hits(cand,BT) and not any(hits(cand,q) for q in placed_rects):
                found=(sn(xx+w/2-mx), sn(yy+h/2-my))
            xx+=1.0
        yy+=1.0
    if found:
        place[r]=(found[0],found[1],0); placed_rects.append(rect(r)); rescued.append(r)
if rescued: print(f"  rescued onto the board: {rescued}")
still=[r for r in place if not (0<=place[r][0]<=100 and 0<=place[r][1]<=90)]
if still: print(f"  STILL off-board: {still}")


def is_smd(libid):
    """classify from the footprint's own attr, not from its library name"""
    m=re.search(r'^\t\(attr ([^)]*)\)', load_fp(libid), re.M)
    return bool(m) and "smd" in m.group(1).split()

_LAYER=re.compile(r'"([FB])\.([A-Za-z]+)"')
def to_back(body):
    """mirror a footprint body onto B.Cu, exactly as KiCad stores a flipped part.

    Verified against a KiCad-written board: back-side footprints hold Y-negated
    coordinates, F/B layer names swapped, and (justify mirror) on every text.
    Arcs survive because KiCad 7+ stores start/mid/end and all three mirror.
    """
    body=_LAYER.sub(lambda m: '"%s.%s"' % ("B" if m.group(1)=="F" else "F", m.group(2)), body)
    def negy(m):
        pre,x,y,rest = m.group(1), m.group(2), m.group(3), m.group(4)
        yv=-float(y)
        return f"({pre} {x} {yv:g}{rest})"
    body=re.sub(r'\((at|start|end|center|mid|xy) ([-\d.]+) ([-\d.]+)([^)]*)\)', negy, body)
    body=re.sub(r'\(effects\n(\s*)\(font', lambda m: f"(effects\n{m.group(1)}(font", body)
    # add mirror to every text effects block that lacks one
    out=[]; i=0
    while True:
        j=body.find("(effects", i)
        if j<0: out.append(body[i:]); break
        d=0;k=j
        while True:
            if body[k]=='(': d+=1
            elif body[k]==')':
                d-=1
                if d==0: break
            k+=1
        blk=body[j:k+1]
        if "justify" not in blk:
            blk=blk[:-1]+"\n\t\t\t\t(justify mirror)\n\t\t\t)"
        elif "mirror" not in blk:
            blk=re.sub(r'\(justify ([^)]*)\)', lambda m:f"(justify {m.group(1)} mirror)", blk, count=1)
        out.append(body[i:j]); out.append(blk); i=k+1
    return "".join(out)

def emit(ref):
    val,libid=comps[ref]
    t=load_fp(libid)
    x,y,rot=place[ref]
    body=t[t.index("\n")+1:t.rindex(")")]
    # these belong to a standalone .kicad_mod, not to a footprint inside a board
    # MUST be line-anchored: unanchored, '\\t(layer' also matches the second tab of
    # '\\t\\t(layer "F.SilkS")' inside every property, silently stripping it.
    body=re.sub(r'^\t\((?:version|generator|generator_version|layer) [^\n]*\)\n', '', body, flags=re.M)
    body=re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m:f'(uuid "{U(ref,m.start())}")', body)
    body=re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', body, count=1)
    body=re.sub(r'\(property "Value" "[^"]*"', f'(property "Value" "{val}"', body, count=1)
    if ref in dnp:                       # merge into the existing attr, never add a second
        if re.search(r'\t\(attr ([^)]*)\)', body):
            body=re.sub(r'\t\(attr ([^)]*)\)', lambda m:f'\t(attr {m.group(1)} dnp)', body, count=1)
        else:
            body='\t(attr dnp)\n'+body
    # bind pads to nets
    pieces=[]; i=0
    while True:
        j=body.find("(pad ", i)
        if j<0: pieces.append(body[i:]); break
        pieces.append(body[i:j])
        d=0; k=j
        while True:
            if body[k]=='(': d+=1
            elif body[k]==')':
                d-=1
                if d==0: break
            k+=1
        blk=body[j:k+1]
        num=re.match(r'\(pad "([^"]*)"', blk).group(1)
        if (ref,num) in padnet:
            code,name=padnet[(ref,num)]
            blk=blk[:-1] + f'\n\t\t\t(net {code} "{name}")\n\t\t)'
        pieces.append(blk); i=k+1
    body="".join(pieces)
    body="".join(("\t"+ln if ln.strip() else ln)+"\n" for ln in body.split("\n")[:-1])
    back = is_smd(libid)
    if back: body=to_back(body)
    layer = "B.Cu" if back else "F.Cu"
    return (f'\t(footprint "{libid}"\n\t\t(layer "{layer}")\n\t\t(uuid "{U(ref)}")\n'
            f'\t\t(at {sn(x+OX)} {sn(y+OY)}{"" if rot==0 else " "+str(rot)})\n' + body + "\t)\n")

skel=open(os.path.join(PCB,"caryatid.kicad_pcb")).read()
head=skel[:skel.index('\t(net 0 "")')]

def top_blocks(text, opener):
    """extract top-level s-expressions by paren balance.

    A regex stopping at the first '\\n\\t)' truncates any block whose body
    contains a line that is exactly one tab and a paren -- which every embedded
    footprint has. That silently produced unbalanced footprints.
    """
    out=[]
    for m in re.finditer(r'^\t\(' + opener, text, re.M):
        i=m.start()+1; d=0; j=i; instr=False
        while j < len(text):
            c=text[j]
            if instr:
                if c=='\\': j+=2; continue
                if c=='"': instr=False
            elif c=='"': instr=True
            elif c=='(': d+=1
            elif c==')':
                d-=1
                if d==0: break
            j+=1
        out.append(text[m.start():j+2])
    return out

graphics="".join(top_blocks(skel,"gr_(?:line|text)"))
mh=top_blocks(skel,'footprint "MountingHole')
nets_txt='\t(net 0 "")\n' + "".join(f'\t(net {i+1} "{n}")\n' for i,n in enumerate(nets))
doc=head + nets_txt + "".join(mh) + graphics + "".join(emit(r) for r in sorted(comps)) + ")\n"
open(os.path.join(PCB,"caryatid.kicad_pcb"),"w").write(doc)
print(f"placed {len(comps)} footprints, {len(nets)} nets, {len(dnp)} DNP")
