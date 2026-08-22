# ADR-080: Five-Weight Promotion Lock

## Status
Proposed promotion, pending Step 78H confirmation.

## Candidate
The proposed five-weight baseline is:

- `rest_weight = 0.20`
- `off_sack_weight = 10.00`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`
- `def_epa_trend_weight = 5.25`

Step 78G selected `def_epa_trend_0525` with `PROVISIONAL_PASS` and improvement
in all four leave-one-season-out views.

## Decision rule
78H performs one final baseline-vs-lock run across 2022–2025. Promotion occurs
only if mean score delta remains negative, mean accuracy degradation is no
worse than -0.2 percentage points, and all four leave-one-season-out views
still improve.
