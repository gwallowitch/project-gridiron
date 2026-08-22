# ADR-049: Third-Down Broad Search

## Status
Accepted for research.

## Context
71A created leakage-safe third-down features, 71B passed historical quality
validation, and 71C added experiment configuration fields.

71D completes runtime/research wiring and performs a broad independent search
for incremental value.

## Baseline
Every experiment retains the current candidate:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

All other parked/rejected research families stay zero.

## Broad grid

Third-down offensive EPA:
- 0.5
- 1.0
- 1.5
- 2.0

Third-down defensive EPA:
- 0.5
- 1.0
- 1.5
- 2.0

Third-down conversion rate:
- 2.0
- 4.0
- 6.0
- 8.0

Third-down stop rate:
- 2.0
- 4.0
- 6.0
- 8.0

Third-and-long conversion rate:
- 2.0
- 4.0
- 6.0
- 8.0

## Missing-data behavior
If either team lacks known third-down history, all third-down adjustments are
neutral-filled to zero.

## Interpretation
71D is a screening step. Only a family showing credible marginal improvement
over `third_down_v1_baseline` earns 71E fine-tuning.
