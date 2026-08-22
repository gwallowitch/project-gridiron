"""Validation for production-safe prediction-time weather snapshots."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "as_of_timestamp",
    "kickoff_timestamp",
    "forecast_retrieved_at",
    "source_id",
    "forecast_temperature_f",
    "forecast_wind_mph",
    "forecast_precip_probability",
    "forecast_condition",
    "roof_state",
    "is_missing",
    "forecast_age_hours",
    "hours_before_kickoff",
}


def validate_prediction_time_weather(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Prediction-time weather is missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame.height == 0:
        return

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Prediction-time weather contains duplicate game_id rows."
        )

    if frame.filter(
        pl.col("as_of_timestamp") >= pl.col("kickoff_timestamp")
    ).height:
        raise ValueError(
            "Prediction-time weather contains as-of timestamps at/after kickoff."
        )

    if frame.filter(
        pl.col("forecast_retrieved_at") > pl.col("as_of_timestamp")
    ).height:
        raise ValueError(
            "Prediction-time weather contains forecasts retrieved after as-of."
        )

    if frame.filter(pl.col("forecast_age_hours") < 0.0).height:
        raise ValueError("Forecast age cannot be negative.")

    if frame.filter(pl.col("hours_before_kickoff") <= 0.0).height:
        raise ValueError("Snapshot must be captured before kickoff.")

    if frame.filter(pl.col("forecast_wind_mph") < 0.0).height:
        raise ValueError("Forecast wind cannot be negative.")

    if frame.filter(
        pl.col("forecast_precip_probability").is_not_null()
        & (
            (pl.col("forecast_precip_probability") < 0.0)
            | (pl.col("forecast_precip_probability") > 1.0)
        )
    ).height:
        raise ValueError(
            "Forecast precipitation probability must be between 0 and 1."
        )
