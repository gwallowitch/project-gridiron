# ADR-036: Rushing Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 68C adds four independent rushing research weights:

- `rush_off_epa_weight`
- `rush_def_epa_weight`
- `rush_success_weight`
- `explosive_run_weight`

All default to zero and must be finite and non-negative.

## Baseline
The current v1.0 candidate retains:
- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

The rushing family is intended to be evaluated incrementally on top of that
baseline in 68D.

## Scope
68C adds configuration/model support only. It does not replace the research grid
and does not promote any rushing signal.
