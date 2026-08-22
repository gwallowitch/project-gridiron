"""Open-Meteo historical-forecast adapter for Project Gridiron.

This adapter intentionally keeps HTTP transport injectable so unit tests never
need the network. It converts Open-Meteo hourly historical-forecast responses
into Project Gridiron's Step 82F prediction-time weather contract.

Important: Open-Meteo's Historical Forecast API is a stitched series of the
first hours of successive forecast runs. It is useful for feasibility work but
does not preserve an exact 2â€“4 hour pre-kickoff forecast vintage for all
2022â€“2025 games. Therefore rows produced by this adapter are explicitly marked
as research-only and must not be used to promote a production weather weight.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import urlopen

import polars as pl

BASE_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

HOURLY_FIELDS = (
    "temperature_2m",
    "wind_speed_10m",
    "precipitation_probability",
    "weather_code",
)


def build_url(
    *,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> str:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_FIELDS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "UTC",
    }
    return f"{BASE_URL}?{urlencode(params)}"


def default_fetch_json(url: str) -> dict:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _nearest_index(times: list[str], kickoff: datetime) -> int:
    kickoff_utc = kickoff.astimezone(UTC)
    parsed = [_parse_utc(value) for value in times]
    return min(
        range(len(parsed)),
        key=lambda index: abs(
            (parsed[index] - kickoff_utc).total_seconds()
        ),
    )


def fetch_game_snapshot(
    *,
    game_id: str,
    kickoff_timestamp: datetime,
    latitude: float,
    longitude: float,
    fetch_json: Callable[[str], dict] = default_fetch_json,
) -> pl.DataFrame:
    """Fetch the stitched historical-forecast value nearest kickoff.

    The resulting timestamp metadata is deliberately conservative:
    `as_of_timestamp` and `forecast_retrieved_at` are set to the selected
    forecast valid hour rather than pretending an exact historical issuance
    time is known. This means the Step 82F strict prediction-time validator
    should NOT be run on these research-only rows.
    """
    kickoff = kickoff_timestamp.astimezone(UTC)
    day = kickoff.date().isoformat()
    payload = fetch_json(
        build_url(
            latitude=latitude,
            longitude=longitude,
            start_date=day,
            end_date=day,
        )
    )

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError(
            f"Open-Meteo returned no hourly forecast rows for {game_id}."
        )

    index = _nearest_index(times, kickoff)
    valid_time = _parse_utc(times[index])

    def value(name):
        values = hourly.get(name)
        if not values or index >= len(values):
            return None
        return values[index]

    # The strict contract requires pre-kickoff timestamps. We cannot honestly
    # infer issuance time from the stitched archive, so create a research frame
    # directly instead of constructing PredictionTimeWeatherSnapshot.
    return pl.DataFrame(
        {
            "game_id": [game_id],
            "kickoff_timestamp": [kickoff],
            "forecast_valid_timestamp": [valid_time],
            "source_id": ["open-meteo-historical-forecast-stitched"],
            "forecast_temperature_f": [value("temperature_2m")],
            "forecast_wind_mph": [value("wind_speed_10m")],
            "forecast_precip_probability": [
                None
                if value("precipitation_probability") is None
                else float(value("precipitation_probability")) / 100.0
            ],
            "forecast_weather_code": [value("weather_code")],
            "latitude": [latitude],
            "longitude": [longitude],
            "research_only": [True],
            "exact_forecast_vintage_known": [False],
        }
    )


def combine_snapshots(frames: list[pl.DataFrame]) -> pl.DataFrame:
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")

