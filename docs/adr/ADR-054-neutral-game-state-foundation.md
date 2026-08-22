# ADR-054: Neutral Game-State Efficiency Foundation

## Status
Accepted for research foundation.

## Context
Pressure/pass-protection research did not improve the current candidate. The next
feature family should improve signal quality rather than add another highly
correlated box-score derivative.

## Decision
73A introduces leakage-safe pregame efficiency measured only in relatively
neutral game states.

A play qualifies when:
- it is a run or pass;
- offense and defense are known;
- absolute offensive score differential is <= 8 points;
- at least 5:00 remains in regulation.

The final five minutes are excluded because play calling and defensive behavior
become increasingly clock- and score-dependent.

## Offensive history
- neutral-state play count;
- EPA/play;
- success rate (`EPA > 0`);
- yards/play;
- explosive-play rate (`yards_gained >= 15`).

## Defensive history
The same metrics are calculated as allowed/faced values.

## Derived home-centered research features
- `neutral_off_epa_difference`
- `neutral_def_epa_difference`
- `neutral_success_difference`
- `neutral_yards_per_play_difference`
- `neutral_explosive_rate_difference`

## Leakage policy
A week-N game uses only same-season observations from weeks strictly less than N.

## Scope
73A creates and persists feature artifacts only. It does not change model
weights or `config/experiments.toml`.

73B will perform historical quality validation before any experiment wiring.
