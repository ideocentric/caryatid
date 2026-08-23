# Conventions for the tools

Rules that apply to **more than one tool**, and that each cost something to
learn. Every one of these lived in a single tool's docstring, where the next
tool to make the same mistake could not see it.

These are not style preferences. Each entry states the rule, the failure that
produced it, and the measurement that proves it — so a future change can tell
whether it is still true rather than taking it on faith.

For decisions about the *board*, see [decisions/](decisions/). This file is
about the code that edits it.

---

## 1. Recompute the zone fill before verifying a copper change

**Any tool that widens, moves, or adds copper must refill the zones before it
asks DRC whether the result is legal.**

A pour holds its clearance from a track by *retreating from it*. Change the
copper and check without refilling, and DRC compares new copper against a pour
drawn for the old geometry. The gap it measures is a fill artefact — a number
describing a board that will never be fabricated.

**What it cost.** `widen_necks.py` widened five Freerouting neck-downs to the
0.20 mm floor and DRC reported one new clearance violation:

```
zone clearance 0.3000 mm; actual 0.2630 mm
Track [/power/TMR] on F.Cu  vs  Zone 'GND plane' [GND]
```

0.263 is 0.300 minus half the 0.075 mm the track grew — the pour standing still.
Tested one at a time, **four of the five were already clean** and only TMR
"failed", against a fill that had not moved. The tool's all-or-nothing rule then
reverted all five. It had been printing "those necks are LOAD-BEARING … it needs
routing space, which is a placement question" since `a68ae67`. They were not,
and it did not.

**The tell:** the conflict was with a **zone**, which retreats, rather than with
a pad or another track, which cannot. A clearance violation against a pour, on
copper you just changed, is suspect until you have refilled.

```python
KPY = ".../Python.framework/Versions/3.9/bin/python3"
subprocess.run([KPY, "-c",
    f"import sys;sys.path.insert(0,'{KSP}');import wx;wx.App(False);"
    f"import pcbnew;b=pcbnew.LoadBoard('{path}');"
    f"pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard('{path}',b)"])
```

`import wx; wx.App(False)` first — pcbnew's Python needs a wxApp to exist before
`ZONE_FILLER` runs, the same requirement `ImportSpecctraSES` has. It still
prints `create wxApp before calling this` on stderr and completes correctly;
that line is noise, not a failure.

**All-or-nothing verification is still right** — a half-widened board reads as
deliberate — but it multiplies the damage of a bad check. One false positive
reverted four sound repairs. Verify the board that would be fabricated.

---

## 2. Collect edits first, apply back to front, and check structure not just parens

Editing s-expression text while iterating over matches shifts every later
offset. Collect all `(offset, old, new)` first, then apply in **one** pass
sorted descending.

**"One pass" is load-bearing, and two descending passes are not equivalent.**
`silk_centre_roles.py` applied footprint-property edits and text edits in two
separate back-to-front passes, both measured against the same original string.
The first pass shifted the file under the second, and `ANALOG BUS` was spliced
inside another label's `(effects)` block.

**Parenthesis balance did not catch it**, because a splice moves parens without
changing their count. `lock_copper.py` corrupted the board the same way earlier,
dropping two segments while staying balanced. Balance is necessary and nowhere
near sufficient. Check structure as well:

```python
if t[off:off + len(old)] != old:
    sys.exit("offset no longer holds what was measured -- not writing")
top  = len(re.findall(r"^\t\(gr_text ", t, re.M))
if top != t.count("(gr_text "):
    sys.exit("a gr_text is no longer at top level -- not writing")
```

What actually surfaced the corruption was `kicad-cli` refusing to parse the
file. **A tool that writes a board should run `kicad-cli pcb drc` afterwards and
treat a non-zero exit as a failed write**, not only as a DRC result.

---

## 3. The collision box must share the anchor the emitter uses

A geometry model that tests one box and draws another is worse than no model:
it reports clearances confidently and wrongly.

- **`conn_labels.py`** tested a **centred** box and emitted `(justify bottom)`,
  which anchors the *bottom*. Every label drew about half a line higher than
  what was checked. The model called J3 a comfortable 0.73 mm clear of
  `CHG LEDS` while DRC reported them overlapping, **six times**, across 22 silk
  violations.
- **`silk_align_connectors.py`** built every reference box horizontally while
  preserving each field's *stored* angle. J9's reference was stored at 90° and
  drew vertical, so a 1.96 × 1.15 box was checked where the board drew
  1.15 × 1.96. The model read 0.47 mm of clearance; DRC found **0.2433**.
- **`pin_labels.surviving_labels`** used `x + up` on both sides of rotated text.
  `th_split` divides line height *asymmetrically* about the anchor, so every
  rotated label got a box of the wrong height, off centre.

Where the anchor cannot be established, **over-reserve**. An obstacle model may
claim more space than the ink needs; it may never claim less.

---

## 4. `P.tw` is a bounding box, so centre with it and never right-align with it

`pin_labels.tw()` returns KiCad's bounding-box width — about 1.1× the inked
width plus a constant. That error is not uniform: it **grows with string
length**.

- **Centring is safe.** The surplus splits evenly either side of a centred
  anchor and cancels; the drawn centre is the anchor whatever the error.
- **Computing an edge is not.** Placing labels at `right - w/2` to right-align
  them indented `GND` about 0.11 mm further than `R`, because the 3-character
  string carries more surplus. The right edges were identical in the model and
  visibly ragged on the board.

To align an edge, emit `(justify right)` and let KiCad find the true edge. The
box then extends *leftward* from the anchor, where over-estimating is the safe
direction.

---

## 5. Silk geometry is centrelines; footprint bounding boxes include markers

Two distinct traps in reading a footprint's silkscreen.

**`fp_line` coordinates are the middle of a 0.12 mm stroke.** The drawn edge is
0.06 mm further out. `silk_audio_baseline.py` measured 0.280 mm of clearance
where DRC found **0.2158**, on J14 and J18. J17's outline ends 0.14 mm sooner
and passed — the kind of near-miss that makes a wrong model look right.

**The bounding box of *all* silk is not the body.** J5 and J11 are IDC box
headers carrying a pin-1 triangle *outside* the outline — J5's at
x 161.780‥162.780 against a body ending at 161.390. Centring on the union put
the label 0.695 mm off, while the body outline, the pad span and the courtyard
all independently agreed on 156.830. Group the segments into connected
components and take the largest; a detached marker then drops out by
construction, with no per-part exception list.

---

## 6. Normalise a lone outlier; exclude only what cannot be fixed

An allow-list is for defects that **cannot** be repaired. Reaching for one to
silence something cheap to fix hides a real inconsistency behind a written
excuse.

**R45** was flagged `lib_footprint_mismatch` because its pads were stored at
270° against a footprint at 90° — 180° *relative*, where `Resistor_SMD` has 0°.
It was **the only one of 64 0603 resistors** on this board like that. The half
turn was harmless (a 0.800 × 0.950 mm rectangle is unchanged by it, and both pad
centres are byte-identical before and after), which is exactly why excusing it
was wrong. It was normalised; the allow-list entry became a comment saying so.

**A1 and A2** are the opposite and belong in the list. All 20 pads of each were
diffed against `caryatid.pretty/DaisySeed_Socket_A_1x20.kicad_mod`: **none
differ**. What differs is what KiCad adds when a footprint is *placed* — `path`,
`sheetfile`, `sheetname`, two property fields and their hide flags. None of it
is copper, and none of it is removable without breaking the schematic link.

The test is not "is it harmless" — both were harmless. It is **"can it be
fixed"**.

---

## 7. Record a hand placement as an override rather than overwriting it

A generator that re-derives positions will revert a deliberate hand adjustment
on its next run, silently, and the person who made it will not be watching.

`silk_audio_baseline.py` carries `ROLE_OVERRIDE` and `REF_OVERRIDE` for J14,
whose `MIC RTN` and reference were placed by hand after the computed positions
read wrong on the shortest jack. Re-running the tool now reproduces the board
instead of fighting it.

Locks are not sufficient: a tool that strips and regenerates its own output by
uuid ignores them. Locks stop an accident; recording the intent stops a re-run.

---

## 8. A fact carried only in conversation will outlive its truth

Not a coding rule, but it cost the most sessions.

An "R45 sits 1.22 mm from the board edge, review with the enclosure in hand"
concern was repeated across four sessions and was never true after `3fe330e`
moved the part. Measured: **5.500 mm**, with J15 and J9 both reaching *further*
toward that edge than R45 does. It survived because it was never written into a
ledger record where it would have been re-checked — the precise failure
`~/.claude/CLAUDE.md`'s ledger methodology exists to prevent. It is now retired
as dated evidence on `BUD-CU-477-interior`.

If a claim matters enough to repeat, it belongs in
[discovery/findings/](../discovery/findings/), not in a summary.