#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ONE-SHOT. Adds the F.Cu ground pour and routes the boost cluster.

Everything else on this board is unrouted and is meant to be done interactively.
This does the two pieces where the geometry is settled and the stakes are high:

  * a GND zone on F.Cu -- that face carries only 21 through-hole parts, so it can
    be a near-solid plane. This is what putting the SMD on the back bought.
  * the boost hot loop. The return is NOT a track: C6's ground pad and U2's
    ground pad each drop a via straight into the plane, so the return runs
    directly under the outgoing current. That is the smallest loop available and
    a track would be strictly worse.

Do not run again: it appends copper, so a second run duplicates it.
"""
import os, sys, re, math, uuid
if os.environ.get("CARYATID_ALLOW_REGEN") != "1":
    sys.exit("refusing to run: one-shot, appends copper and would duplicate on a second run")
PCB=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","hardware","pcb","caryatid.kicad_pcb")
NS=uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
def U(*k): return str(uuid.uuid5(NS,"caryatid-route:"+":".join(map(str,k))))
t=open(PCB).read()
# '(zone' alone matches '(zone_connect' inside QFN pads -- anchor to top level
if re.search(r'^\t\(zone\b', t, re.M): sys.exit("refusing: the board already has a zone")

nets={m.group(2):int(m.group(1)) for m in re.finditer(r'^\t\(net (\d+) "([^"]*)"\)', t, re.M)}

def fp(ref):
    for m in re.finditer(r'^\t\(footprint "([^"]+)"', t, re.M):
        i=m.start(); d=0; j=i
        while True:
            c=t[j]
            if c=='(': d+=1
            elif c==')':
                d-=1
                if d==0: break
            j+=1
        b=t[i:j+1]
        r=re.search(r'\(property "Reference" "([^"]+)"', b)
        if r and r.group(1)==ref: return b
    raise KeyError(ref)

def pad(ref, num):
    """physical pad centre: rotation is applied at compute time, not stored"""
    b=fp(ref)
    m=re.search(r'^\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b, re.M)
    ox,oy,rot = float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)
    th=math.radians(rot); cs,sn=math.cos(th),math.sin(th)
    pm=re.search(r'\(pad "%s"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)' % re.escape(num), b)
    px,py=float(pm.group(1)),float(pm.group(2))
    return (round(ox+px*cs+py*sn,3), round(oy-px*sn+py*cs,3))

def seg(a,b,width,net,tag):
    return (f'\t(segment\n\t\t(start {a[0]} {a[1]})\n\t\t(end {b[0]} {b[1]})\n'
            f'\t\t(width {width})\n\t\t(layer "B.Cu")\n\t\t(net {net})\n\t\t(uuid "{U(tag)}")\n\t)\n')
def via(p,net,tag):
    return (f'\t(via\n\t\t(at {p[0]} {p[1]})\n\t\t(size 0.6)\n\t\t(drill 0.3)\n'
            f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net {net})\n\t\t(uuid "{U(tag)}")\n\t)\n')

# every back-side pad, so via placement is searched rather than eyeballed
def all_back_pads():
    out=[]
    for m in re.finditer(r'^\t\(footprint "([^"]+)"', t, re.M):
        s=m.start(); d=0; k=s
        while True:
            c=t[k]
            if c=='(': d+=1
            elif c==')':
                d-=1
                if d==0: break
            k+=1
        b=t[s:k+1]
        if '(layer "B.Cu")' not in b[:200]: continue
        am=re.search(r'^\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b, re.M)
        ox,oy,rot=float(am.group(1)),float(am.group(2)),float(am.group(3) or 0)
        th=math.radians(rot); cs,sn=math.cos(th),math.sin(th)
        for pm in re.finditer(r'\(pad "([^"]*)"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s*\n\s*\(size ([-\d.]+) ([-\d.]+)\)(?:.|\n){0,400}?\(net \d+ "([^"]*)"\)', b):
            px,py = float(pm.group(2)), float(pm.group(3))
            w,h   = float(pm.group(4)), float(pm.group(5))
            rx, ry = px*cs+py*sn, -px*sn+py*cs
            if rot in (90,270): w,h = h,w
            out.append((ox+rx, oy+ry, w, h, pm.group(6)))
    return out
BACKPADS=all_back_pads()

def free_via(near, net, r=0.3, clr=0.25):
    """nearest spot to `near` where a via clears every back pad of another net"""
    for radius in [x*0.25 for x in range(2,40)]:
        for ang in range(0,360,10):
            x=round(near[0]+radius*math.cos(math.radians(ang)),3)
            y=round(near[1]+radius*math.sin(math.radians(ang)),3)
            ok=True
            for px,py,w,h,pnet in BACKPADS:
                if pnet==net: continue
                if abs(x-px) < w/2+r+clr and abs(y-py) < h/2+r+clr: ok=False; break
            if ok: return (x,y)
    raise RuntimeError("no free via location")

out=[]
NECK=0.2
def escape(p, to_x, net, tag):
    mid=(to_x, p[1])
    return seg(p, mid, NECK, net, tag+"-neck"), mid

# +5V_RAW: pin 6 down to C6, which now sits below U2
p6=pad("U2","6"); c61=pad("C6","1")
kink=(p6[0], round((p6[1]+c61[1])/2,3))
out.append(seg(p6, kink, NECK, nets["+5V_RAW"], "raw-neck"))
out.append(seg(kink, c61, 0.8, nets["+5V_RAW"], "raw-wide"))

# SW: pin 5 straight across to L1, which is now level with it. This is the net
# the rearrangement was for -- 1.5 A peak and the loudest radiator on the board.
p5=pad("U2","5"); l2=pad("L1","2")
s,mid = escape(p5, 66.4, nets["/power/SW"], "sw")
out.append(s); out.append(seg(mid, l2, 1.2, nets["/power/SW"], "sw-wide"))
s,mid = escape(pad("U2","3"), 61.9, nets["VOUT"], "vout-c4")
out.append(s); out.append(seg(mid, pad("C4","1"), 1.2, nets["VOUT"], "vout-c4-wide"))
out.append(seg(pad("L1","1"), pad("C5","1"), 1.2, nets["VOUT"], "vout-c5"))

# hot-loop return: into the plane, vias placed by search
for ref,padnum,tag in (("C6","2","c6"),("U2","4","u2")):
    p0=pad(ref,padnum)
    v=free_via(p0, "GND")
    out.append(seg(p0, v, NECK, nets["GND"], "gnd-"+tag))
    out.append(via(v, nets["GND"], "v-"+tag))
    print(f"  GND via for {ref}.{padnum}: {v}  ({math.hypot(v[0]-p0[0],v[1]-p0[1]):.2f} mm from the pad)")

# --- F.Cu ground plane -------------------------------------------------------
OX,OY,W,H,INSET = 50.0, 30.0, 100.0, 90.0, 0.6
x0,y0,x1,y1 = OX+INSET, OY+INSET, OX+W-INSET, OY+H-INSET
zone=(f'\t(zone\n\t\t(net {nets["GND"]})\n\t\t(net_name "GND")\n\t\t(layer "F.Cu")\n'
      f'\t\t(uuid "{U("zone")}")\n\t\t(name "GND plane")\n\t\t(hatch edge 0.5)\n'
      '\t\t(connect_pads\n\t\t\t(clearance 0.3)\n\t\t)\n'
      '\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n'
      '\t\t(fill yes\n\t\t\t(thermal_gap 0.3)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n'
      '\t\t(polygon\n\t\t\t(pts\n'
      f'\t\t\t\t(xy {x0} {y0}) (xy {x1} {y0}) (xy {x1} {y1}) (xy {x0} {y1})\n'
      '\t\t\t)\n\t\t)\n\t)\n')
out.append(zone)

assert t.rstrip().endswith(")")
open(PCB,"w").write(t.rstrip()[:-1] + "".join(out) + ")\n")
print(f"added {len(out)-1} copper items + 1 GND zone on F.Cu")
for a,b,lbl in (("U2","C6","+5V_RAW U2.6->C6.1"),):
    pass
import math as _m
d=lambda a,b: _m.hypot(a[0]-b[0],a[1]-b[1])
print(f"  hot loop out : U2.6 -> C6.1  {d(pad('U2','6'),pad('C6','1')):.2f} mm, 0.8 mm wide")
print(f"  hot loop back: vias to plane at C6.2 and U2.4 (no track)")
print(f"  SW node      : U2.5 -> L1.2  {d(pad('U2','5'),pad('L1','2')):.2f} mm, routed at 1.2 mm")
