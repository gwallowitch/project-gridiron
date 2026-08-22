# ADR-125 — Combined-Model Historical Diagnostics

## Context

Step 88A froze the six-weight model contract and recorded a stable fingerprint.

The project now shifts from feature discovery to evaluating the behavior of the
locked model as a whole.

## Decision

Step 88B produces historical diagnostics for 2022–2025:

- winner accuracy;
- Brier score;
- log loss;
- margin MAE and RMSE when available;
- probability concentration;
- model-home-favorite and model-away-favorite splits;
- high-confidence and close-probability splits;
- 10-point calibration buckets;
- expected calibration error;
- season-to-season stability ranges.

The validator verifies the Step 88A model fingerprint before generating
diagnostics.

Game-level artifacts are discovered from the existing backtest/prediction
locations. The script requires a recognized home-win probability column and
derives actual outcomes from either the artifact or schedule.

## Consequence

Step 88B does not tune the model. It measures the locked model.

The results determine Step 88C: probability calibration diagnostics and
candidate calibration transforms without changing feature weights.
