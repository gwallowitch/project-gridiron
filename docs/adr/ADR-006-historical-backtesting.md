# ADR-006: Historical Prediction Backtesting

## Status
Accepted

## Context
Prediction Engine v1 produces leak-free pregame predictions, but model quality cannot be improved responsibly without comparing those predictions with completed game results.

## Decision
Project Gridiron will evaluate persisted predictions against final `home_score` and `away_score` values from the persisted schedule. The first release reports winner accuracy, Brier score, log loss, margin MAE/RMSE, coverage, pick-side accuracy, and probability calibration.

Tied and incomplete games are excluded. Predictions remain immutable inputs; the backtester does not regenerate them using final-season information.

## Consequences
- Model changes can be evaluated against a stable baseline.
- Backtesting requires completed score columns in the schedule dataset.
- Probability and margin parameters remain uncalibrated until multi-season results are available.
