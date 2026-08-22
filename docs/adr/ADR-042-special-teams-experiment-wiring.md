# ADR-042: Special Teams Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 70C adds four independent special-teams research weights:

- `fg_make_rate_weight`
- `punt_coverage_weight`
- `punt_return_weight`
- `punt_touchback_weight`

All default to zero and must be finite and non-negative.

## Baseline
The current model candidate remains:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

Special teams will be evaluated incrementally on top of that baseline in 70D.

## Scale caution
Punt coverage/return features are measured in yards and have materially larger
raw dispersion than field-goal and touchback-rate features. 70D should therefore
use smaller punt-yardage weights.

## Scope
70C adds experiment configuration support only. Runtime/research wiring and the
broad special-teams search belong to 70D.
