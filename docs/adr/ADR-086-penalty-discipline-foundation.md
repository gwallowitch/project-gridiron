# ADR-086: Penalty Discipline Foundation

## Status
Accepted for Step 80A research foundation.

## Context
Step 79 promoted defensive schedule difficulty, creating a six-weight research
baseline. The next feature family should add information that is relatively
orthogonal to efficiency, recent form, field position, and strength of
schedule.

## Decision
Step 80A introduces leakage-safe penalty-discipline features derived from
accepted penalty attribution and penalty yards in play-by-play.

The family measures:
- offensive penalties per 100 plays;
- offensive penalty yards per 100 plays;
- defensive penalties per 100 plays;
- defensive penalty yards per 100 plays;
- total penalty count and yardage burden.

## Matchup features
- `penalty_yards_discipline_advantage`
- `penalty_rate_discipline_advantage`
- `offensive_penalty_discipline_advantage`
- `defensive_penalty_discipline_advantage`

Positive matchup values favor the home team because they are computed as
away-team penalty burden minus home-team penalty burden.

## Leakage control
Only weeks strictly earlier than the target game are included.

## Frozen Step 80 baseline
- rest = 0.20
- offensive sack = 10.00
- punt return = 0.24
- long-field avoidance = 1.00
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

80A creates artifacts only. 80B will validate historical coverage and
dispersion before any experiment wiring.
