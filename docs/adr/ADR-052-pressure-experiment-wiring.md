# ADR-052: Pressure Experiment Wiring

## Status
Accepted for research wiring.

## Decision
72C adds five independent pressure/pass-protection research weights:

- `pass_protection_weight`
- `pressure_creation_weight`
- `clean_dropback_weight`
- `pressured_off_epa_weight`
- `pressured_def_epa_weight`

All default to zero and must be finite and non-negative.

## Current candidate baseline
Pressure research remains incremental on top of:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

Third-down remains parked at zero after 71D failed to show meaningful
incremental value.

## Scope
72C changes configuration/data-model support only. It does not replace
`config/experiments.toml`.

72D will add runtime/research wiring and the broad pressure search.
