# ADR-043: Special Teams Broad Search

## Status
Accepted for research.

## Context
70A created leakage-safe special-teams artifacts. 70B showed strong coverage,
reasonable field-goal/touchback distributions, and noisier punt-yardage
features. 70C added special-teams configuration fields.

70D completes runtime/research wiring and performs a broad independent search.

## Baseline
Every configuration retains:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

Previously parked feature families remain zero.

## Broad search

Field-goal make-rate difference:
- 1.0
- 2.0
- 4.0
- 6.0

Punt coverage advantage:
- 0.05
- 0.10
- 0.15
- 0.20

Punt return advantage:
- 0.05
- 0.10
- 0.15
- 0.20

Punt touchback advantage:
- 1.0
- 2.0
- 4.0
- 6.0

Punt-yardage weights are intentionally small because their raw dispersion is
several yards per game and includes occasional large outliers.

## Missing-data behavior
When either team lacks known prior special-teams history, the special-teams
adjustments are neutral-filled to zero. This preserves Week 1 and sparse early
field-goal samples without fabricating performance.

## Interpretation
70D is a screening step. Only a family showing credible marginal improvement
over `special_teams_v1_baseline` earns 70E fine-tuning.
