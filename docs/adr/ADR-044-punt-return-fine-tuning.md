# ADR-044: Punt Return Fine Tuning

## Status
Accepted for research.

## Context
70D identified `punt_return_advantage` as the only special-teams feature with a
clear monotonic improvement pattern. The broad-search weights 0.05, 0.10, 0.15,
and 0.20 all improved composite score versus the current v1 baseline, and the
largest tested value remained the best candidate.

The 0.20 candidate produced:
- 3-1 season record versus baseline;
- positive mean accuracy delta;
- improved composite score;
- a confidence interval whose upper bound was only slightly above zero.

## Decision
70E fine-tunes only `punt_return_weight`.

Grid:
- 0.00 baseline
- 0.12
- 0.14
- 0.16
- 0.18
- 0.20
- 0.22
- 0.24
- 0.26
- 0.30

This provides local resolution around 0.20 while also testing whether the broad
search stopped before the optimum.

## Baseline
Every experiment retains:
- `rest_weight = 0.20`
- `off_sack_weight = 10.0`

All other research-family weights remain zero.

## Promotion rule
70E does not force promotion. The final decision in 70F should consider:
- cross-season composite score;
- season W-L-T;
- paired confidence interval;
- accuracy delta;
- whether performance peaks or continues improving at the upper boundary.
