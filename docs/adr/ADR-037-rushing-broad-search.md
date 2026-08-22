# ADR-037: Rushing Broad Search

## Status
Accepted for research.

## Context
68A produced leakage-safe rushing artifacts and 68B validated roughly 94.4%
coverage with stable distributions. 68C added rushing configuration fields.

This milestone also completes the runtime/research wiring required for non-zero
rushing weights so the broad search cannot silently ignore the new signals.

## Decision
68D tests four rushing families independently on top of the current v1.0
candidate baseline, which retains `off_sack_weight = 10.0`.

Search ranges:

- rushing offense EPA/play: 1, 2, 4, 6
- rushing defense EPA/play: 1, 2, 4, 6
- rushing success rate: 5, 10, 15, 20
- explosive run rate: 10, 20, 30, 40

The baseline experiment has all rushing weights at zero.

## Interpretation
Only features that improve on the `rushing_v1_baseline` earn further
fine-tuning. Do not promote directly from the broad search.
