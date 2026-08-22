# ADR-077: Recent-Form Experiment Wiring

## Status
Accepted for isolated research wiring.

## Decision
78C adds six independent recent-form research weights:

- `recent_off_epa_weight`
- `recent_def_epa_weight`
- `off_epa_trend_weight`
- `def_epa_trend_weight`
- `off_success_trend_weight`
- `def_success_trend_weight`

All default to zero and must be finite and non-negative.

## Research baseline
Recent-form research remains incremental on the current four-weight lock:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`

Rejected fourth-down, explosive-suppression, and turnover-stability families
remain parked at zero.

## Scope
78C adds configuration/result-model support only. It does not replace
`config/experiments.toml` and does not yet wire recent-form artifacts into
runtime scoring.

78D will complete runtime/research wiring and execute a broad isolated search
over the six validated recent-form signals.
