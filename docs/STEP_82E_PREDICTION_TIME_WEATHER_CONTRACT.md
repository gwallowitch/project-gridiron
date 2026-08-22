# Step 82E — Prediction-Time Weather Contract

## Purpose

Historical observed weather has shown a small but repeatable research signal.
That is not sufficient for live deployment.

A live Project Gridiron weather feature must be computable entirely from
information available before the model's decision timestamp.

## Required production contract

A production-safe environment artifact must record:

- `game_id`;
- `as_of_timestamp`;
- `kickoff_timestamp`;
- forecast source identifier;
- forecast retrieval timestamp;
- forecast temperature;
- forecast sustained wind speed;
- forecast precipitation probability or categorical condition;
- known roof / indoor state at the decision timestamp;
- data freshness / age;
- missing-data indicator.

## No-leakage rules

1. `as_of_timestamp` must be earlier than kickoff.
2. Forecast retrieval time must be no later than `as_of_timestamp`.
3. Post-kickoff observed temperature, wind, precipitation, or roof changes may
   not be substituted into a prediction-time artifact.
4. If a forecast value is unavailable, the model must use the documented
   neutral/missing behavior rather than a later observed value.
5. Backtests intended to support production promotion must recreate the
   prediction-time snapshot, not use final game observations.

## Step 82E status

The historical robustness test can produce a `PROVISIONAL_PASS`, but
`production_eligible` remains `false`.

A later step must build or acquire historical forecast snapshots and verify
that the prediction-time version preserves the historical signal before any
weather weight is promoted into the live model.
