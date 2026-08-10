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

def is_smd(libid):
    """classify from the footprint's own attr, not from its library name"""
    m=re.search(r'^\t\(attr ([^)]*)\)', load_fp(libid), re.M)
    return bool(m) and "smd" in m.group(1).split()

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

ZONES={  # back-side zones. The strip under BT1 is the largest genuinely free
 # area on this face: the cell's only pads are its two end terminals.
 "anabus":  (17,3,50,24),      # analogue bus + its RC, under the cell
 "audio":   (52,3,84,24),      # audio block, under the cell
 "seedsup": (41,28,51,60),     # A10/A11 networks, between the Seed pad columns
 "digbus":  (31,62,50,80),     # digital bus series resistors
 "switch":  (56,26,64,78),     # 74HC14 channel, clear of both socket columns
 "charger": (1,26,30,50),      # charger, left, under the power connectors
 "boost":   (6,62,30,86),      # boost cluster is hand-placed inside this
 "conn":    (66,62,84,80),     # RGB / I2C / sensor resistors
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

# --- the front: BT1, the Seed, and a deliberate connector ring --------------
# Cables leave a vertical JST upward, so "facing outward" matters less than
# staying clear of the 21 mm cell and the Seed, and sitting near what they feed.
# Left edge = power and the digital bus (near A1); right edge = analogue and
# audio (near A2, far from the boost); bottom edge = switches and module ports.
#
# Edges are STACKED from measured extents rather than hand-placed. Hand
# arithmetic on rotated courtyard offsets kept producing touching parts.

def extent(ref, rot):
    w,h,mx,my = bbox(comps[ref][1])
    if rot in (90,270): w,h,mx,my = h,w,-my,mx
    return w,h,mx,my

def stack(refs, axis, fixed, start, gap, rot):
    """lay refs along `axis` from `start`, so measured extents tile with `gap`"""
    out={}; cur=start
    for r in refs:
        w,h,mx,my = extent(r,rot)
        if axis=="y":
            out[r]=(fixed, round(cur + h/2 - my, 2), rot); cur += h + gap
        else:
            out[r]=(round(cur + w/2 - mx, 2), fixed, rot); cur += w + gap
    return out

ANCHOR={"BT1":(13.55,14.0,0), "A1":(38.0,29.0,0), "A2":(53.24,29.0,0),
        "J11":(23,42,0),      # digital bus IDC, inboard beside A1
        "J5":(70,42,0),       # analogue bus IDC, inboard beside A2
        "J14":(80,76,0),      # mic bias return -> hook switch second pole
        "J18":(80,66,0),      # audio in, beside J14 -- same loom
        "J16":(66,68,0)}      # expansion / SPI1, inboard right
# Everything stays at rotation 0. A vertical JST exits upward, so orienting the
# pin row along the edge buys nothing -- and the rotated-courtyard transform is
# the one piece of geometry here I could not verify, so it is not used.
ANCHOR.update(stack(["J1","J2","J3","J4"], "y", 6.5, 29.0, 2.0, 0))          # left: power
ANCHOR.update(stack(["J12","J9","J10","J17"], "y", 88.5, 26.0, 2.0, 0))      # right: RGB, sensors, audio out
ANCHOR.update(stack(["J6","J7","J8","J13B","J15"], "x", 85.0, 10.0, 1.5, 0)) # bottom: switches, module ports

# --- the back: hand-placed clusters, the rest shelf-packed -------------------
# A back-side pad sits at (X + px, Y - py): the body is stored Y-negated. So on
# U2 (SOT-563) the pins land GND top-right, SW middle-right, VOUT bottom-right.
#
# The hot loop on a boost is VOUT -> C6 -> GND -> back into the IC ground pin,
# and the SW node is the radiator. C6 therefore sits hard against pin 6 and L1
# hard against pin 5. L1 is turned 180 so its SW pad faces the IC -- 180 is
# (px,py) -> (-px,-py), which is checkable, unlike the 90 transform.
UX,UY = 14.0, 74.0
# Spacings below are computed from measured courtyards (all centre offsets are
# zero), not eyeballed. C6 takes the one adjacent slot because the output cap
# carries the discontinuous current and is the dominant radiator; L1 gets the
# next-best position above the IC.
BACK_ANCHOR={
 "U2":(UX,UY,0),                 # courtyard 2.40 x 1.90
 "C6":(17.3, 74.5, 0),           # pad 1 -> pin 6, 1.64 mm
 "L1":(15.0, 70.2, 180),         # 180 faces the SW pad at the IC
 "C4":(10.5, 73.5, 180),         # pad 1 -> pin 3, 1.44 mm
 "C5":(19.4, 70.5, 0),           # at L1's VOUT pad
 "R7":(10.9, 76.5, 0),           # FB divider, against pin 1
 "R8":(10.9, 78.6, 0),
 "FB1":(21.5, 74.5, 0),          # ferrite, downstream of +5V_RAW
 # C7 (100 uF, 9.6 x 7.1) is bulk after the ferrite, not loop-critical. Hand-
 # anchoring put it on the J6/J7 pads, so the keepout-aware packer places it.
}

def tht_keepouts():
    """front through-hole pads occupy every copper layer -- keepouts for the back"""
    out=[]
    for r,(val,libid) in comps.items():
        if is_smd(libid) or r not in ANCHOR: continue
        x,y,rot = ANCHOR[r]
        for m in re.finditer(r'\(pad "[^"]*" (thru_hole|np_thru_hole)[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s*\n\s*\(size ([-\d.]+) ([-\d.]+)\)', load_fp(libid)):
            px,py,sw,sh = (float(m.group(i)) for i in (2,3,4,5))
            if rot==180: px,py=-px,-py
            out.append((x+px-sw/2-0.3, y+py-sh/2-0.3, x+px+sw/2+0.3, y+py+sh/2+0.3))
    for hx,hy in [(5,5),(95,5),(5,85),(95,85)]:
        out.append((hx-3.6,hy-3.6,hx+3.6,hy+3.6))
    # hand-anchored back parts are keepouts too -- the packer would otherwise
    # drop shelf-packed parts straight on top of the boost cluster
    for r,(x,y,rot) in BACK_ANCHOR.items():
        w,h,mx,my=bbox(comps[r][1])
        if rot==180: mx,my=-mx,-my
        out.append((x+mx-w/2-0.4, y+my-h/2-0.4, x+mx+w/2+0.4, y+my+h/2+0.4))
    return out
KEEP=tht_keepouts()
def blocked(x0,y0,x1,y1):
    return any(not (x1<=k[0] or k[2]<=x0 or y1<=k[1] or k[3]<=y0) for k in KEEP)

def shelf(zname, refs):
    x0,y0,x1,y1=ZONES[zname]
    items=sorted(refs, key=lambda r:-bbox(comps[r][1])[1])
    out={}; over=[]; cx,cy,rowh=x0,y0,0.0
    for r in items:
        w,h,mx,my=bbox(comps[r][1]); w+=1.0; h+=1.0
        tries=0
        while True:
            if cx+w>x1:
                cx=x0; cy+=rowh+0.8; rowh=0.0
            if not blocked(cx,cy,cx+w,cy+h) or tries>400: break
            cx+=0.5; tries+=1
        if cy+h>y1: over.append(r)
        out[r]=(sn(cx+w/2-mx), sn(cy+h/2-my), 0)
        cx+=w; rowh=max(rowh,h)
    if over: print(f'  zone {zname}: {len(over)} parts past its bottom edge -> {over}')
    return out

place=dict(ANCHOR); place.update(BACK_ANCHOR)
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
            if (not hits(cand,BT) and not blocked(*cand)
                    and not any(hits(cand,q) for q in placed_rects)):
                found=(sn(xx+w/2-mx), sn(yy+h/2-my))
            xx+=1.0
        yy+=1.0
    if found:
        place[r]=(found[0],found[1],0); placed_rects.append(rect(r)); rescued.append(r)
if rescued: print(f"  rescued onto the board: {rescued}")
# front-side collision check: rotated extents, courtyard + 0.3 mm
def frect(r):
    w,h,mx,my=bbox(comps[r][1]); x,y,rot=place[r]
    if rot in (90,270): w,h,mx,my=h,w,-my,mx
    return (x+mx-w/2-0.3, y+my-h/2-0.3, x+mx+w/2+0.3, y+my+h/2+0.3, r)
fr=[frect(r) for r in comps if not is_smd(comps[r][1])]
# the four M3 holes live in the skeleton, not in comps -- the first version of
# this check omitted them and passed a board where J6 and J18 fouled a hole
for hx,hy in [(5,5),(95,5),(5,85),(95,85)]:
    fr.append((hx-3.4, hy-3.4, hx+3.4, hy+3.4, f"MH@{hx},{hy}"))
clash=[(a[4],b_[4]) for i,a in enumerate(fr) for b_ in fr[i+1:]
       if not (a[2]<=b_[0] or b_[2]<=a[0] or a[3]<=b_[1] or b_[3]<=a[1])]
print("  front collisions:", clash if clash else "none")
outside=[a[4] for a in fr if a[0]<0 or a[1]<0 or a[2]>100 or a[3]>90]
print("  front parts breaking the outline:", outside if outside else "none")

# back-side collisions (rot 0 or 180 only, so the bbox transform is exact)
def brect(r):
    w,h,mx,my=bbox(comps[r][1]); x,y,rot=place[r]
    if rot==180: mx,my=-mx,-my
    return (x+mx-w/2-0.2, y+my-h/2-0.2, x+mx+w/2+0.2, y+my+h/2+0.2, r)
br=[brect(r) for r in comps if is_smd(comps[r][1])]
# A through-hole pad on the front occupies EVERY copper layer, so it is a
# keepout for back-side SMD. Courtyard-vs-courtyard checks never see this:
# the front part is on the other face. Missing it put the A10/A11 network and
# the 74HC14 straight on top of the Seed sockets' pad columns.
def thtpads(r):
    fp=load_fp(comps[r][1]); x,y,rot=place[r]; out=[]
    for m in re.finditer(r'\(pad "[^"]*" (thru_hole|np_thru_hole)[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s*\n\s*\(size ([-\d.]+) ([-\d.]+)\)', fp):
        px,py,sw,sh=float(m.group(2)),float(m.group(3)),float(m.group(4)),float(m.group(5))
        if rot==180: px,py=-px,-py
        out.append((x+px-sw/2-0.25, y+py-sh/2-0.25, x+px+sw/2+0.25, y+py+sh/2+0.25))
    return out
keep=[]
for r in comps:
    if not is_smd(comps[r][1]): keep += thtpads(r)
for hx,hy in [(5,5),(95,5),(5,85),(95,85)]:
    keep.append((hx-3.4,hy-3.4,hx+3.4,hy+3.4))
foul=sorted({a[4] for a in br for k in keep
             if not (a[2]<=k[0] or k[2]<=a[0] or a[3]<=k[1] or k[3]<=a[1])})
print(f"  back parts over front through-hole pads: {len(foul)}" + (f" -> {foul[:12]}{' ...' if len(foul)>12 else ''}" if foul else " (none)"))
bc=[(a[4],b_[4]) for i,a in enumerate(br) for b_ in br[i+1:]
    if not (a[2]<=b_[0] or b_[2]<=a[0] or a[3]<=b_[1] or b_[3]<=a[1])]
print(f"  back collisions: {len(bc)}" + (f" -> {bc[:6]}{' ...' if len(bc)>6 else ''}" if bc else " (none)"))

def padpos(ref,pin):
    for n,px,py,_,_ in symlib.pins_resolved.__self__ if False else []: pass
    t=load_fp(comps[ref][1])
    m=re.search(r'\(pad "%s"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)' % re.escape(pin), t)
    px,py=float(m.group(1)),float(m.group(2))
    x,y,rot=place[ref]
    if rot==180: px,py=-px,-py
    return (x+px, y-py)          # back side: body stored Y-negated
p6=padpos("U2","6"); p4=padpos("U2","4"); p5=padpos("U2","5")
c6a=padpos("C6","1"); c6b=padpos("C6","2"); l1b=padpos("L1","2")
import math
def d(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
print(f"  boost hot loop: U2.6->C6 {d(p6,c6a):.2f} mm, C6->U2.4 return {d(c6b,p4):.2f} mm, "
      f"perimeter {d(p6,c6a)+d(c6a,c6b)+d(c6b,p4)+d(p4,p6):.2f} mm")
print(f"  SW node: U2.5 -> L1.2 = {d(p5,l1b):.2f} mm")

still=[r for r in place if not (0<=place[r][0]<=100 and 0<=place[r][1]<=90)]
if still: print(f"  STILL off-board: {still}")


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
        if yv==0: yv=0.0          # avoid emitting "-0", which reads as a diff
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
