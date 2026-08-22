# ADR-035: Rushing Feature Foundation

## Status
Accepted for research foundation.

## Decision
Milestone 68A introduces leakage-safe pregame rushing features built from
nflverse play-by-play.

Initial offensive metrics:
- rush EPA/play;
- rushing success rate;
- explosive-run rate;
- rushing play volume.

Initial defensive metrics:
- rush EPA allowed/play;
- rushing success rate allowed;
- explosive-run rate allowed;
- rushing play volume faced.

Explosive runs are defined as gains of at least 10 yards.

Quarterback kneels are excluded when `qb_kneel` is available. Other rush attempts
remain eligible.

## Leakage rule
For a game in week N, only same-season play-by-play from weeks strictly less
than N may contribute.

## Week 1
Week 1 has no same-season prior rushing history. Known flags are false and raw
difference features remain null.

## Scope
68A is standalone. It does not modify experiment weights, research scoring, or
production predictions.
