# ADR-053: Pressure Broad Search

## Status
Accepted for research.

## Context
72A created leakage-safe pressure/pass-protection features, 72B passed the
historical quality gate, and 72C added experiment fields.

72D completes runtime/research wiring and runs an independent broad search for
incremental value.

## Baseline
Every experiment retains the current candidate:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

Third-down and other parked research families remain zero.

## Broad grid

Rate-based features:
- pass protection advantage: 5, 10, 15, 20
- pressure creation advantage: 5, 10, 15, 20
- clean dropback advantage: 5, 10, 15, 20

EPA-based features:
- pressured offense EPA difference: 0.5, 1.0, 1.5, 2.0
- pressured defense EPA advantage: 0.5, 1.0, 1.5, 2.0

The rate-family scale is intentionally similar to the previously useful sack-rate
weight. EPA weights are smaller because the raw EPA feature scale is materially
larger than a rate difference.

## Missing data
If either team lacks known prior pressure history, the pressure adjustments are
neutral-filled to zero.

## Interpretation
72D is a screening step. Only a family with credible marginal improvement over
`pressure_v1_baseline` advances to 72E fine-tuning.
