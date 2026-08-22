# ADR-100 — Open-Meteo Historical Forecast Feasibility

## Decision

Use Open-Meteo as the first low-cost weather archive adapter for Project
Gridiron research, but do not treat its Historical Forecast API as proof of a
strict 2–4 hour pre-kickoff forecast vintage for the entire 2022–2025 window.

## Why

Open-Meteo documents a Historical Forecast API with coverage beginning around
2021/2022. It includes temperature, 10 m wind speed, precipitation probability,
weather code, and other hourly variables. No API key is required for its public
API.

However, the Historical Forecast API is a continuous hourly series constructed
by stitching the first hours of successive operational model runs. It is not
the same as selecting one exact historical model run issued 2–4 hours before
kickoff.

Open-Meteo's Single Runs API is the better conceptual match for strict
no-lookahead reconstruction, but broad run-level archives do not cover the
full 2022–2025 NFL study period. ECMWF IFS single runs reach back to March 2024,
while most other individual-run archives begin much later.

## Consequence

Step 82G is a feasibility and ingestion step. It can determine whether forecast
wind behaves similarly to the observed-weather high-wind signal, but it cannot
by itself promote `high_wind_050`.

All 82G rows are explicitly marked:
- `research_only = true`
- `exact_forecast_vintage_known = false`
- `production_eligible = false`

If the signal survives, the next task is a stricter vintage source for the
promotion backtest, potentially NOAA/NOMADS or another archived model-run
source.
