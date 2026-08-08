# 0001 — Record architecture decisions

- **Status**: Accepted
- **Date**: 2026-08-08

## Context

This board is meant to outlive the instrument that prompted it, and to be picked
up by someone — including a later version of its author — who was not present
for the reasoning. A frozen pin map without recorded reasons is a list of
arbitrary constraints, and arbitrary constraints get quietly broken.

## Decision

Significant decisions get a numbered record here. Records are **append-only**:
once accepted, a record is never rewritten, only superseded by a later one.

A decision belongs here if reversing it would cost a board spin, or if the
reasoning is not recoverable from the schematic.

## Consequences

The pin map states *what*; these records state *why*. When a future build wants
a pin that is already taken, the record says what it is taken for and what
paying for it would cost.