# ADR-065: Fourth-Down Experiment Wiring

## Status
Accepted for research wiring.

## Decision
75C adds five independent fourth-down research weights:

- `fourth_down_off_epa_weight`
- `fourth_down_def_epa_weight`
- `fourth_down_conversion_weight`
- `fourth_down_stop_weight`
- `fourth_short_conversion_weight`

All default to zero and must be finite and non-negative.

## Research baseline
Fourth-down research is incremental on the Step 74F locked candidate:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`

The current aggregate research benchmark remains approximately 0.4668.

## Scope
75C adds configuration/result-model support only. It does not replace
`config/experiments.toml` and does not yet wire fourth-down artifacts into the
runtime scorer.

75D will complete runtime/research wiring and run the broad fourth-down search.
