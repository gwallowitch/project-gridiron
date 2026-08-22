"""Validation for Step 81 travel-fatigue artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "travel_geography_known",
    "away_travel_miles",
    "away_time_zone_shift_hours",
    "eastward_time_zone_shift_hours",
    "westward_time_zone_shift_hours",
    "cross_country_travel",
    "long_haul_travel",
    "travel_rest_known",
    "short_week_away",
    "short_week_travel_miles",
    "short_week_time_zone_shift",
}


def validate_travel_fatigue_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Travel-fatigue features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Travel-fatigue features contain duplicate game_id values.")

    known = frame.filter(pl.col("travel_geography_known"))
    if known.filter(pl.col("away_travel_miles") < 0.0).height:
        raise ValueError("Travel miles cannot be negative.")
    if known.filter(pl.col("away_time_zone_shift_hours") < 0.0).height:
        raise ValueError("Time-zone shift cannot be negative.")
    if known.filter(pl.col("away_time_zone_shift_hours") > 3.0).height:
        raise ValueError("Domestic home-market time-zone shift exceeded 3 hours.")
