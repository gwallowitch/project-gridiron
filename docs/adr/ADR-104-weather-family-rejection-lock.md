# ADR-104 — Weather Family Rejection Lock

## Decision

Close Step 82 and park the weather family.

## Evidence

Step 82E found an apparently robust observed-weather signal, with
`high_wind_050` receiving a historical robustness `PROVISIONAL_PASS`.

Step 82H then materialized forecast-derived weather for all four research
seasons with 100% wind coverage.

Step 82I tested whether that signal survived when high wind was derived from
forecast data instead of final observed weather.

It did not.

Across 2022–2025:
- the forecast-wind baseline won all four seasons;
- every forecast high-wind candidate had a positive mean score delta;
- every candidate had a 0-4 season record;
- forecast_high_wind_010, the least-bad candidate, still degraded score by
  +0.0001 and accuracy by -0.1%;
- larger weights degraded performance further.

This is strong evidence that the observed-weather signal was not sufficiently
transferable to forecast-based inputs.

## Consequence

No weather weight is promoted.

All weather and travel fields remain available for future research but are
locked to zero in the active model.

The promoted six-weight baseline remains:
- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.0
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

## Next

Step 83 should move to a genuinely new feature family rather than spending more
research budget on weather tuning.
