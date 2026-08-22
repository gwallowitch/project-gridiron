# ADR-040: Drive Efficiency Broad Search

## Status
Accepted for research.

## Context
69A created leakage-safe drive-efficiency artifacts. 69B showed stable
distributions and substantial prior-drive sample depth. 69C added five drive
configuration fields.

69D completes runtime/research wiring and performs the first independent broad
search on top of the current v1 candidate.

## Baseline
Every configuration retains:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

All previously parked/rejected feature families stay at zero.

## Broad search

Drive offense EPA/drive:
- 0.25
- 0.50
- 0.75
- 1.00

Drive defense EPA allowed/drive:
- 0.25
- 0.50
- 0.75
- 1.00

Scoring-drive rate:
- 2.5
- 5.0
- 7.5
- 10.0

Touchdown-drive rate:
- 2.5
- 5.0
- 7.5
- 10.0

Plays per drive:
- 0.25
- 0.50
- 0.75
- 1.00

These ranges are deliberately moderate because EPA/drive and plays/drive have
substantially larger raw dispersion than rate features.

## Interpretation
69D is a screening step. Only a family showing credible marginal improvement
over `drive_v1_baseline` earns a 69E fine-tuning search.
