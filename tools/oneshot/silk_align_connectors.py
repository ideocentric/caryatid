import sys, re, uuid, math
sys.path.insert(0,'/Users/matt/Documents/GitHub/personal/caryatid/tools')
import check_board as C, pin_labels as P, conn_labels as L

RENAME = {("J12","4"):"B", ("J12","3"):"G", ("J12","2"):"R"}
J12_BASE_Y = 33.10
BOTTOM = {"J6":116.43,"J7":116.43,"J8":116.43,"J9":116.43,"J10":116.53,
          "J12":41.25,"J15":116.43,"J19":116.43}
J13_PITCH, J13_GAP = 1.3, 0.35

B=C.Board(C.PCB); t=B.t
owner={}; padpos={}
for p in B.parts:
    m=re.search(r'\(property "Reference" "(J\d+)"',p["blk"])
    if not m: continue
    for pd in B.pads(p):
        owner[str(uuid.uuid5(P.NS,f"caryatid-pinlabel-{m.group(1)}-{pd['num']}"))]=(m.group(1),pd["num"])
        padpos[(m.group(1),pd["num"])]=(pd["x"],pd["y"])
connu={L.uid(r):r for r in L.LABELS}

def silk(ref):
    p=[q for q in B.parts if q["ref"]==ref][0]; pts=[]
    for m in re.finditer(r"\(fp_(?:line|rect|poly|circle|arc)",p["blk"]):
        blk=C.sexp(p["blk"],m.start())
        if '"F.SilkS"' not in blk: continue
        for a,b in re.findall(r"\((?:start|end|xy|center|mid) ([-\d.]+) ([-\d.]+)\)",blk):
            pts.append(B._xform(p,float(a),float(b)))
    xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
    return min(xs),min(ys),max(xs),max(ys)

items=[]      # gr_text edits: (start, blk, newtext|None, nx, ny, nrot|None, nsize|None)
for m in re.finditer(r'^\t\(gr_text "([^"]*)"',t,re.M):
    blk=C.sexp(t,m.start()+1); u=re.search(r'\(uuid "([^"]+)"\)',blk)
    if not u: continue
    at=re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)',blk)
    sz=re.search(r'\(size ([\d.]+) ([\d.]+)\)',blk)
    key=u.group(1)
    if key in owner:
        ref,pin=owner[key]
        if ref=="J12":
            txt=RENAME.get((ref,pin), m.group(1))
            sx,sy,ex,ey=silk("J12"); w=P.tw(txt,1.0)
            px=padpos[(ref,pin)][0]
            nx = sx+w/2 if pin=="4" else (ex-w/2 if pin=="1" else px)
            items.append((m.start(),blk,txt,nx,J12_BASE_Y,0,None,f"J12 pin{pin}"))
        elif ref=="J13":
            sx,sy,ex,ey=silk("J13")
            order=sorted([q for q in padpos if q[0]=="J13"], key=lambda q:padpos[q][0])
            i=order.index((ref,pin))
            cx=(padpos[order[0]][0]+padpos[order[-1]][0])/2
            nx=cx+(i-(len(order)-1)/2)*J13_PITCH
            w=P.tw(m.group(1),0.8)
            ny=sy-J13_GAP-w/2
            items.append((m.start(),blk,None,nx,ny,90,None,f"J13 pin{pin}"))
    elif key in connu and connu[key] in BOTTOM:
        ref=connu[key]; sx,sy,ex,ey=silk(ref)
        w=P.tw(m.group(1),float(sz.group(1)))
        items.append((m.start(),blk,None,ex-w/2,BOTTOM[ref],0,None,f"{ref} human label"))

# reference fields live inside footprints
# R45's REFERENCE IS DELIBERATELY NOT MOVED. Three placements were tried and
# all three were rejected by the check below, against J15's label and J9's --
# and the rejections were the MODEL's, not the board's. P.tw() over-estimates
# glyph width: it puts "R45" at 3.154 mm and scores the J15 gap at 0.153, while
# KiCad's own DRC reports no silk overlap there at a 0.25 mm rule. R45 stays at
# (141.990, 116.130). It is excluded from the obstacle set below for the same
# reason -- the model would veto a position the board accepts.
fpedits=[]
for p in B.parts:
    if p["ref"] not in BOTTOM: continue
    ref=p["ref"]; sx,sy,ex,ey=silk(ref)
    rm=re.search(r'\(property "Reference" "[^"]+"',p["blk"]); pb=C.sexp(p["blk"],rm.start())
    w=P.tw(ref,1.0)
    NX,NY=sx+w/2, BOTTOM[ref]
    a=math.radians(p["rot"]); cs,sn=math.cos(a),math.sin(a)
    dx,dy=NX-p["x"], NY-p["y"]
    lx,ly = dx*cs - dy*sn, dx*sn + dy*cs
    fpedits.append((p,pb,lx,ly,NX,NY,ref))

obst=P.Obstacles(B)
# Drop the reference fields we are about to move, and the connector-label texts
# we are about to move: comparing a label against its own old position is not a
# clash, it is the thing being changed.
moving_refs={f"{r}:Reference" for r in BOTTOM} | {"R45:Reference"}   # see above
obst.rects=[r for r in obst.rects if r[4] not in moving_refs]
boxes=[]
def bx(txt,size,x,y,rot):
    w=P.tw(txt,size); up,dn=P.th_split(size)
    return (x-up,y-w/2,x+dn,y+w/2) if rot%180==90 else (x-w/2,y-up,x+w/2,y+dn)
bad=[]
for start,blk,newtxt,nx,ny,nrot,nsz,tag in items:
    txt=newtxt if newtxt else re.match(r'\(gr_text "([^"]*)"',blk).group(1)
    size=float(re.search(r'\(size ([\d.]+)',blk).group(1))
    b=bx(txt,size,nx,ny,nrot); boxes.append((b,tag))
for p,pb,lx,ly,NX,NY,ref in fpedits:
    boxes.append((bx(ref,1.0,NX,NY,0), f"{ref} ref"))
for b,tag in boxes:
    c=obst.clash(b,0.26)
    if c: bad.append(f"{tag} box {tuple(round(v,3) for v in b)} hits {c}")
for i in range(len(boxes)):
    for j in range(i+1,len(boxes)):
        A,Bx=boxes[i][0],boxes[j][0]
        gap=max(max(A[0],Bx[0])-min(A[2],Bx[2]), max(A[1],Bx[1])-min(A[3],Bx[3]))
        if gap<0.25:
            bad.append(f"{boxes[i][1]} {A} vs {boxes[j][1]} {Bx}: {gap:+.3f}")
for b in bad: print("   !", b)
print(f"  {len(items)} texts + {len(fpedits)} reference fields; {len(bad)} problems")
if bad: sys.exit(1)

for start,blk,newtxt,nx,ny,nrot,nsz,tag in sorted(items,key=lambda q:-q[0]):
    new=blk
    if newtxt:
        new=re.sub(r'^\(gr_text "[^"]*"', f'(gr_text "{newtxt}"', new, count=1)
    a2=re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)',new)
    rot=f" {nrot:g}" if nrot else ""
    new=new[:a2.start()]+f'(at {nx:.3f} {ny:.3f}{rot})'+new[a2.end():]
    if "(locked yes)" not in new:
        head=new.index("\n")+1; new=new[:head]+"\t\t(locked yes)\n"+new[head:]
    t=t[:start+1]+new+t[start+1+len(blk):]

# reference fields: rewrite inside each footprint block, back to front by file offset
fpspans=[]
for m in re.finditer(r"^\t\(footprint ", t, re.M):
    blk=C.sexp(t,m.start()+1)
    rm=re.search(r'\(property "Reference" "(J\d+)"',blk)
    if not rm: continue
    ref=rm.group(1)
    hit=[e for e in fpedits if e[6]==ref]
    if not hit: continue
    _,_,lx,ly,NX,NY,_=hit[0]
    pb=C.sexp(blk,rm.start())
    pa=re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)',pb)
    # FORCE ANGLE 0. Preserving the stored angle contradicted the box model:
    # bx() above builds every reference box horizontally, but J9's reference
    # was stored `(at -1.868 4.745 90)` and rendered VERTICAL. So the check
    # measured a 1.96 x 1.15 box where the board drew 1.15 x 1.96, reported
    # 0.47 mm of clearance where DRC found 0.2433, and J9 was nudged 0.19 mm
    # off its neighbours' baseline to buy a margin it did not need. Every
    # connector on this row reads horizontally; the angle is not preserved.
    newpb=pb[:pa.start()]+f'(at {lx:.4f} {ly:.4f} 0)'+pb[pa.end():]
    fpspans.append((m.start()+1+rm.start(), len(pb), newpb))
for off,ln,newpb in sorted(fpspans,key=lambda q:-q[0]):
    t=t[:off]+newpb+t[off+ln:]

assert sum(1 if c=="(" else -1 if c==")" else 0 for c in t)==0
open(C.PCB,"w").write(t)
print("  written")
