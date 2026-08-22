# ADR-071: Turnover-Stability Foundation

## Status
Accepted for research foundation.

## Context
Step 76 rejected explosive/chunk-play suppression as an incremental model
input. The current research lock remains:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.00

with an aggregate benchmark near 0.4668.

The next family should separate repeatable turnover skill from noisy fumble
recovery outcomes rather than simply adding raw turnover margin.

## Decision
77A creates leakage-safe pregame turnover-stability features from same-season
play-by-play history strictly before the target week.

The feature family distinguishes:
- turnover protection;
- takeaway creation;
- interception protection;
- interception creation;
- offensive fumble-loss luck;
- defensive fumble-recovery luck;
- combined fumble-recovery luck.

## Derived matchup features
- `turnover_protection_advantage`
- `takeaway_creation_advantage`
- `interception_protection_advantage`
- `interception_creation_advantage`
- `off_fumble_luck_advantage`
- `def_fumble_luck_advantage`
- `combined_fumble_recovery_luck`

Positive skill-oriented values favor the home team. Fumble-recovery measures
are explicitly labeled as luck/regression candidates rather than stable skill.

## Scope
77A builds and persists features only. It does not alter experiment weights,
runtime scoring, `config/experiments.toml`, or the four-weight research lock.

77B will validate historical coverage, dispersion, and sample depth before any
experiment wiring.
