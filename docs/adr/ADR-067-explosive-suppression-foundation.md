# ADR-067: Explosive-Play Suppression Foundation

## Status
Accepted for research foundation.

## Context
Step 75 rejected fourth-down efficiency as an incremental model input. The
current research lock remains:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.00

with an aggregate benchmark near 0.4668.

The next family should measure game-changing field-flipping plays rather than
another down-specific efficiency metric.

## Decision
76A creates leakage-safe pregame explosive/chunk-play features from scrimmage
plays.

Definitions:
- chunk play: gain of at least 10 yards;
- explosive play: gain of at least 20 yards.

Pregame team histories use only same-season weeks strictly before the target
game.

## Derived matchup features
- `explosive_off_rate_difference`
- `explosive_suppression_advantage`
- `chunk_off_rate_difference`
- `chunk_suppression_advantage`
- `explosive_yards_share_difference`

Positive defensive suppression values favor the home team.

## Scope
76A builds and persists features only. It does not change experiment weights,
runtime scoring, `config/experiments.toml`, or the Step 74F research benchmark.

76B will validate historical coverage, dispersion, and sample depth before any
model wiring.
