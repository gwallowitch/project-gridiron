# ADR-045: Punt Return Provisional Promotion

## Status
Accepted as a provisional v1 candidate.

## Context
70D identified `punt_return_advantage` as the only special-teams feature with a
clear monotonic improvement pattern. 70E then fine-tuned `punt_return_weight`
from 0.12 through 0.30.

The best region was a plateau around 0.22–0.26:

- 0.22: score delta about -0.0019, accuracy delta +0.6%, 3-1 seasons
- 0.24: score delta about -0.0019, accuracy delta +0.6%, 3-1 seasons
- 0.26: score delta about -0.0019, accuracy delta +0.6%, 3-1 seasons

The paired 95% confidence intervals still narrowly included zero, so the signal
was not statistically conclusive under the automated promotion rule.

## Decision
Lock `punt_return_weight = 0.24` as a **provisional** v1 candidate.

The current candidate weights are:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`

All other researched feature weights remain zero.

## Why 0.24 instead of 0.26
0.24 and 0.26 were effectively tied on aggregate score, accuracy, and season
record. 0.24 is preferred as the slightly more conservative coefficient within
the observed plateau, reducing overfit risk without giving up measured
performance.

## Validation policy
This is not treated as statistically proven. It must remain subject to forward
validation during the opening weeks of the next regular season before any
betting workflow relies on it.

## Scope
70F records and tests the lock. It does not add another feature family and does
not alter the promotion thresholds.
