# ADR-039: Drive Efficiency Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 69C adds five independent drive-efficiency research weights:

- `drive_off_epa_weight`
- `drive_def_epa_weight`
- `scoring_drive_rate_weight`
- `td_drive_rate_weight`
- `plays_per_drive_weight`

All default to zero and must be finite and non-negative.

## Baseline
The current model candidate remains:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

The drive-efficiency family will be tested incrementally on top of that baseline
in 69D.

## Scope
69C adds experiment configuration support only. It does not replace
`config/experiments.toml`, alter the broad research grid, or promote any drive
feature.
