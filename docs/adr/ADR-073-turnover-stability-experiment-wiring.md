# ADR-073: Turnover-Stability Experiment Wiring

## Status
Accepted for research wiring.

## Decision
77C adds seven independent research weights:

- `turnover_protection_weight`
- `takeaway_creation_weight`
- `interception_protection_weight`
- `interception_creation_weight`
- `off_fumble_luck_weight`
- `def_fumble_luck_weight`
- `combined_fumble_luck_weight`

All default to zero and must be finite and non-negative.

## Research baseline
Turnover-stability research remains incremental on the current four-weight lock:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`

The rejected fourth-down and explosive-suppression families remain parked at
zero.

## Interpretation
The first four weights represent skill-oriented turnover behavior. The three
fumble weights are explicitly treated as luck/regression candidates. Their
predictive direction must therefore be learned empirically rather than assumed
from raw recovery percentage.

## Scope
77C adds configuration/result-model support only. It does not replace
`config/experiments.toml` and does not yet wire turnover-stability artifacts
into runtime scoring.

77D will complete runtime/research wiring and execute the broad search.
