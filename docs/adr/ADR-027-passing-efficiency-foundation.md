# ADR-027: Passing Efficiency Foundation

## Status
Accepted for research foundation.

## Decision
Milestone 66A builds leakage-safe pregame passing-efficiency features from
nflverse play-by-play.

Initial offensive metrics:
- EPA per quarterback dropback
- passing success rate
- sack rate suffered
- explosive-pass rate

Initial defensive metrics:
- EPA allowed per opponent dropback
- passing success rate allowed
- sack rate generated
- explosive-pass rate allowed

Game-level home-centered differences are persisted for later research.

## Dropback definition
If nflverse provides `qb_dropback`, that field is used. Otherwise the builder
falls back to plays where `pass_attempt == 1` or `sack == 1`.

## Leakage rule
For a game in week N, only play-by-play from weeks strictly less than N in the
same season may contribute. Current-game and future-week plays are excluded by
construction.

## Week 1
Week 1 has no same-season prior history and is represented with known flags set
to false and null raw differences. A later experiment layer may neutral-fill
those rows while retaining the coverage flags.

## Scope
66A is standalone. It does not wire passing features into experiment scoring or
production predictions. Opponent adjustment beyond the offense/defense split is
deferred until historical artifacts are validated.
