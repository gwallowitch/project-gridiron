# ADR-056: Neutral Game-State Experiment Wiring

## Status
Accepted for research wiring.

## Decision
73C adds five independent neutral-state research weights:

- `neutral_off_epa_weight`
- `neutral_def_epa_weight`
- `neutral_success_weight`
- `neutral_yards_per_play_weight`
- `neutral_explosive_weight`

All default to zero and must be finite and non-negative.

## Current candidate baseline
Neutral-state research remains incremental on top of:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

Pressure and third-down remain parked after failing to add meaningful
cross-season value.

## Scope
73C changes configuration/data-model support only. It does not replace
`config/experiments.toml`.

73D will add runtime/research wiring and the broad neutral-state search.
