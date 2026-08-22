# ADR-041: Special Teams Feature Foundation

## Status
Accepted for research foundation.

## Context
Project Gridiron has one promoted incremental signal so far:
`off_sack_weight = 10.0`. Red-zone, rushing, and drive-efficiency families did
not justify promotion. Milestone 70 therefore moves to a more independent
special-teams family.

## Decision
70A introduces leakage-safe pregame special-teams features built from nflverse
play-by-play.

Initial components:

Field goals:
- make rate;
- average attempt distance;
- 50+ yard attempt rate.

Punting / coverage:
- punt attempts;
- opponent punt return yards allowed;
- punt touchback rate.

Punt returns:
- punt return yards gained.

Derived home-centered differences:
- `fg_make_rate_difference`
- `punt_coverage_advantage`
- `punt_return_advantage`
- `punt_touchback_advantage`

## Leakage rule
For a game in week N, only same-season special-teams plays from weeks strictly
less than N may contribute.

## Week 1
Week 1 has no same-season prior special-teams history. Known flags are false and
derived differences remain null.

## Scope
70A creates and validates artifacts only. It does not modify experiment weights
or production prediction behavior.
