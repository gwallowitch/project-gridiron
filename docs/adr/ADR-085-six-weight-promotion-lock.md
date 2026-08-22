# ADR-085: Six-Weight Promotion Lock

## Status
Proposed promotion, pending Step 79F confirmation.

## Candidate

The proposed six-weight baseline is:

- `rest_weight = 0.20`
- `off_sack_weight = 10.00`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`
- `def_epa_trend_weight = 5.25`
- `defensive_schedule_difficulty_weight = 2.25`

## Evidence

Step 79E selected `def_sos_225` with `PROVISIONAL_PASS`.

Its robustness profile was:

- mean score delta approximately -0.000468;
- mean accuracy delta effectively flat;
- season record 3-1;
- leave-one-season-out improvement 4/4;
- worst leave-one-season-out delta remained favorable.

## Decision rule

79F performs a final baseline-vs-candidate run across 2022–2025.

Promotion requires:

1. negative mean selection-score delta;
2. mean winner-accuracy degradation no worse than -0.2 percentage points;
3. improvement in all four leave-one-season-out views;
4. worst leave-one-season-out result must still favor the candidate.

If all gates pass, the six-weight model becomes the research baseline for
Step 80 onward.
