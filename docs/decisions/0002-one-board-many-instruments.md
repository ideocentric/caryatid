# 0002 — One board, many instruments, in its own repository

- **Status**: Accepted
- **Date**: 2026-08-08

## Context

Several instruments — absonus, loa, baby borg — need the same things: a
single-cell charger with power path, a boost to feed a Daisy Seed, charge and
battery indication, audio jacks and coupling, and a way to get pots, switches
and sensors onto pins. Each had been solving it separately.

loa's requirement P-11 already stated the conclusion: *the power module must be
reusable independently of the Daisy Seed, as a component for other projects. Its
interface is a connector and a documented pinout, not a shared PCB.*

## Decision

**One PCB layout serves every instrument.** Every variable element enters through
a connector; a build populates the subset it needs. Order once, stuff per
instrument.

**It lives in its own repository**, consumed by each instrument as a submodule.
Not inside loa, and not in a monorepo with the instruments.

## Consequences

**Good:**

- The power, charge and indicator sections get designed once and reviewed once.
- An instrument's hardware directory holds only what is peculiar to it.
- The board can be versioned and released independently of any instrument.

**Bad:**

- A second repository to keep, and a licence conversation of its own — see
  [0006](0006-licensing-is-open.md).
- Submodules are a friction every contributor pays, including the author.
- A change wanted by one instrument now affects three. That is the point, and it
  is also the cost.

**Neutral:**

- The instruments keep their own licences. This board's licence is not settled
  by loa's ADR 0006 and must not be assumed from it.