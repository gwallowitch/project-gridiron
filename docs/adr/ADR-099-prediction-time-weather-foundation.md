# ADR-099 — Prediction-Time Weather Foundation

Step 82E produced a PROVISIONAL_PASS for `high_wind_050`:

- mean score delta = -0.000246;
- 4/4 season wins;
- 4/4 leave-one-season-out wins;
- worst LOOSO delta = -0.000131.

The historical signal is robust enough to justify work on production-safe
weather data, but not to promote the weight itself.

Step 82F therefore stops weight tuning and defines the required forecast
snapshot contract.

A valid snapshot must be captured before kickoff and may use only forecast data
retrieved no later than the model's `as_of_timestamp`.

The foundation deliberately does not fetch forecasts. Historical forecast
archives vary by provider and licensing, so source acquisition should be a
separate decision after the contract is stable.
