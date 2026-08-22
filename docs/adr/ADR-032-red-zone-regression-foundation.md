# ADR-032: Red-Zone Regression Foundation

## Status
Accepted for research foundation.

## Decision
Milestone 67A introduces leakage-safe pregame red-zone features built from
nflverse play-by-play.

A red-zone play is defined as an offensive play snapped with `yardline_100`
greater than 0 and less than or equal to 20.

Initial offensive metrics:
- red-zone EPA per play;
- red-zone success rate;
- red-zone touchdown-play rate;
- red-zone play volume.

Initial defensive metrics:
- red-zone EPA allowed per play;
- red-zone success rate allowed;
- red-zone touchdown-play rate allowed;
- red-zone play volume faced.

Game-level home-centered differences are persisted for later research.

## Leakage rule
For a game in week N, only same-season play-by-play from weeks strictly less
than N may contribute. Current-game and future-week plays are excluded by
construction.

## Why play-level touchdown rate first
67A intentionally starts with a simple, auditable play-level touchdown rate
rather than inferring drive-level red-zone trips from an unverified drive schema.
If historical validation shows the feature family is useful, a later milestone
may add drive/trip conversion metrics after the source fields are explicitly
verified.

## Week 1
Week 1 has no same-season prior history. Known flags are false and raw
differences remain null. Later experiment wiring may neutral-fill these rows.

## Scope
67A is standalone. It does not alter experiments, research weights, or
production predictions.
