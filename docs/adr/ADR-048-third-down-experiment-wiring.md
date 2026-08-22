# ADR-048: Third-Down Experiment Wiring

## Status
Accepted for research wiring.

## Decision
71C adds five independent third-down research weights:

- `third_down_off_epa_weight`
- `third_down_def_epa_weight`
- `third_down_conversion_weight`
- `third_down_stop_weight`
- `third_and_long_weight`

All default to zero and must be finite and non-negative.

## Current candidate baseline
Third-down research will be incremental on top of the current candidate:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

## Scope
71C adds experiment configuration support only. It does not replace
`config/experiments.toml`. Runtime/research wiring plus the broad third-down
search belongs to 71D.
