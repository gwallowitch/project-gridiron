# ADR-057: Neutral Game-State Broad Search

## Status
Accepted for research.

## Context
73A created leakage-safe neutral-state efficiency features, 73B passed the
historical quality gate, and 73C added experiment fields.

73D completes runtime/research wiring and screens each neutral-state feature for
incremental cross-season value.

## Baseline
Every experiment retains:
- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

Third-down and pressure remain parked at zero.

## Broad grid
Neutral offense EPA:
- 0.5, 1.0, 1.5, 2.0

Neutral defense EPA:
- 0.5, 1.0, 1.5, 2.0

Neutral success rate:
- 5, 10, 15, 20

Neutral yards/play:
- 0.25, 0.50, 0.75, 1.00

Neutral explosive rate:
- 5, 10, 15, 20

## Missing data
If either team lacks prior neutral-state history, all neutral-state adjustments
are neutral-filled to zero.

## Interpretation
Only a family showing credible incremental improvement over
`neutral_state_v1_baseline` earns 73E fine-tuning.
