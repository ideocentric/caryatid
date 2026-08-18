# Artwork

## `enso-oro.svg`

The house mark. **Original work by Matt Comeione, drawn in Adobe Illustrator**,
used across the instrument projects — absonus, loa, baby borg — and on this
carrier board. First party, so it places no constraint on how this design is
licensed.

That provenance is recorded because the file itself cannot answer it: the
Illustrator export carries no metadata, no author, no `<title>`, no licence and
no download record, and the question "does anything here block a copyleft
licence?" came down entirely to who drew this. Anyone auditing later should not
have to ask again.

**It is committed rather than left in `local/`** for two reasons. It is the
source the silkscreen is generated *from* — the board holds 153 derived
polygons, which are an output, not a source — and CERN-OHL-S, the licence
[ADR 0006](../../docs/decisions/0006-licensing-is-open.md) is heading toward,
defines Complete Source as the editable design files. A repo whose logo exists
only as flattened polygons would not meet that.

Regenerate the silkscreen with:

```
.venv/bin/python tools/svg_to_silk.py --size 18 --at 174,55.5 --apply
```

Size is not arbitrary — see the tool's header. It is measured off the
fabricated absonus v0.3 board, not chosen.
