"""Validation for Step 82A game-environment features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "temperature_f",
    "wind_mph",
    "weather_text",
    "roof_text",
    "surface_text",
    "stadium_text",
    "indoor_or_closed_roof",
    "retractable_roof",
    "rain_or_precipitation",
    "snow_or_wintry",
    "extreme_cold",
    "extreme_heat",
    "high_wind",
    "environment_known",
    "adverse_weather_count",
    "adverse_weather",
}


def validate_game_environment_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Game-environment features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Game-environment features contain duplicate game_id values."
        )

    if frame.filter(pl.col("wind_mph") < 0.0).height:
        raise ValueError("Wind speed cannot be negative.")

    if frame.filter(pl.col("adverse_weather_count") < 0).height:
        raise ValueError("Adverse-weather count cannot be negative.")

    if frame.filter(pl.col("adverse_weather_count") > 5).height:
        raise ValueError("Adverse-weather count exceeded expected maximum.")
