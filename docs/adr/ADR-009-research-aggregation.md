# ADR-009: Cross-Season Research Aggregation

## Status

Accepted

## Decision

Aggregate each experiment across all seasons in a research profile using
the arithmetic mean of:

- winner accuracy
- Brier score
- log loss
- margin MAE
- margin RMSE
- selection score

Also report season wins, best and worst season, and average selection-score
difference from `rest_000_baseline`.

## Scope

This milestone ranks cross-season averages but does not perform statistical
significance testing or authorize automatic model promotion.
