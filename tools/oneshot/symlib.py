# SPDX-License-Identifier: GPL-3.0-or-later
"""KiCad symbol-library reader used by the one-shot schematic bootstrap.

Read-only helper: parses .kicad_sym, resolves (extends ...), and returns pin
positions so labels can be placed at pin endpoints. Safe to import.
"""
import re, os
KSYM="/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
PROJ="/Users/matt/Documents/GitHub/personal/caryatid/hardware/pcb/caryatid.kicad_sym"

def _libpath(lib):
    return PROJ if lib=="caryatid" else os.path.join(KSYM, lib+".kicad_sym")

def _balanced(t, i):
    """return text of the s-expression starting at index i (t[i]=='(')"""
    d=0; j=i; instr=False
    while j < len(t):
        c=t[j]
        if instr:
            if c=='\\': j+=2; continue
            if c=='"': instr=False
        elif c=='"': instr=True
        elif c=='(': d+=1
        elif c==')':
            d-=1
            if d==0: return t[i:j+1]
        j+=1
    raise ValueError("unbalanced")

_cache={}
def symbol_text(lib, name):
    key=(lib,name)
    if key in _cache: return _cache[key]
    t=open(_libpath(lib)).read()
    m=re.search(r'^\t\(symbol "%s"' % re.escape(name), t, re.M)
    if not m: raise KeyError(f"{lib}:{name} not found")
    s=_balanced(t, m.start()+1)
    _cache[key]=s
    return s

def pins(lib, name):
    """[(number, x, y, angle, etype)] in SYMBOL coords (+y up)"""
    s=symbol_text(lib,name); out=[]
    for m in re.finditer(r'\(pin\s+(\S+)\s+\S+\s*\n', s):
        blk=_balanced(s, m.start())
        etype=m.group(1)
        at=re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)', blk)
        num=re.search(r'\(number\s+"([^"]*)"', blk)
        if at and num:
            out.append((num.group(1), float(at.group(1)), float(at.group(2)), int(at.group(3)), etype))
    return out

def resolve(lib, name):
    """follow (extends ...) to the ancestor that owns the graphics/pins"""
    chain=[name]
    cur=name
    while True:
        s=symbol_text(lib,cur)
        m=re.search(r'\(extends "([^"]+)"', s)
        if not m: break
        cur=m.group(1); chain.append(cur)
        if len(chain)>8: raise ValueError("extends loop")
    return cur, chain

def pins_resolved(lib,name):
    root,_=resolve(lib,name)
    return pins(lib,root)

def flat_entry(lib, name):
    """self-contained (symbol "Lib:Name") for lib_symbols.

    Non-derived symbols are embedded VERBATIM with only the outer name changed --
    anything else loses tokens like (power) and trips lib_symbol_mismatch, which in
    turn stops PWR_FLAG working and cascades into power_pin_not_driven errors.
    """
    root,chain=resolve(lib,name)
    if root==name:
        s=symbol_text(lib,name)
        return "\t"+s.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"',1)
    raise NotImplementedError(f"{lib}:{name} is derived (extends {root}); use a base symbol instead")
