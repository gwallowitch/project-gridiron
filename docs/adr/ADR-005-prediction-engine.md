# ADR-005: Prediction Engine v1

## Status
Accepted

## Decision
Predict each Week N game using Week N-1 PGR values, a 1.5-point home-field adjustment, and a logistic probability transform. Week 1 uses neutral 100 ratings because no prior-week PGR exists.

## Consequences
The engine is deterministic, explainable, and free of same-week leakage. Parameters are baseline assumptions and must be calibrated through historical backtesting before being treated as optimized estimates.
