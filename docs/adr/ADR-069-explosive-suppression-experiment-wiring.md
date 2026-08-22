# ADR-069: Explosive-Suppression Experiment Wiring

## Status
Accepted for research wiring.

## Decision
76C adds five independent research weights:

- `explosive_off_rate_weight`
- `explosive_suppression_weight`
- `chunk_off_rate_weight`
- `chunk_suppression_weight`
- `explosive_yards_share_weight`

All default to zero and must be finite and non-negative.

## Research baseline
Explosive-suppression research remains incremental on the Step 74F lock:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`

The fourth-down family from Step 75 remains parked at zero.

## Scope
76C adds experiment configuration/result-model support only. It does not
replace `config/experiments.toml` and does not wire the new artifact into the
runtime scorer.

76D will complete runtime/research wiring and execute the broad search.
