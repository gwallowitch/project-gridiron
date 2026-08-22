# ADR-101 — Open-Meteo Schedule Materialization

Step 82H connects the 82G adapter to Project Gridiron's schedule data and NFL
home-stadium coordinates.

The output is one research forecast row per game where a home stadium can be
resolved and the Open-Meteo response succeeds.

The materialized data remains explicitly research-only because Open-Meteo's
Historical Forecast API does not preserve the exact historical issuance vintage
needed for a strict 2–4 hour pre-kickoff production backtest.

Step 82H therefore answers a narrower question: can a forecast-based wind
signal be reconstructed at useful coverage across 2022–2025?

If coverage is healthy, the next step should join the materialized forecast
wind to the experiment runner and compare a forecast-derived high-wind feature
against the current observed-weather `high_wind_050` research signal.
