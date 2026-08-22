# ADR-060: Field Position Experiment Wiring

## Status
Accepted for research wiring.

## Decision
74C adds five independent field-position / hidden-yards research weights:

- `off_start_field_position_weight`
- `def_field_position_weight`
- `short_field_rate_weight`
- `long_field_avoidance_weight`
- `hidden_yards_field_position_weight`

All default to zero and must be finite and non-negative.

## Current candidate baseline
Field-position research remains incremental on top of:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

Neutral-state, pressure, and third-down remain parked after failing to add
credible cross-season value.

## Scope
74C changes experiment configuration/data-model support only. It does not
replace `config/experiments.toml`.

74D will add runtime/research wiring and the broad field-position search.
