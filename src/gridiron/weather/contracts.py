"""Prediction-time weather snapshot contract.

Step 82F does not fetch forecasts. It defines the production-safe schema that
future historical forecast snapshots must satisfy.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime

import polars as pl


@dataclass(frozen=True, slots=True)
class PredictionTimeWeatherSnapshot:
    game_id: str
    as_of_timestamp: datetime
    kickoff_timestamp: datetime
    forecast_retrieved_at: datetime
    source_id: str
    forecast_temperature_f: float | None = None
    forecast_wind_mph: float | None = None
    forecast_precip_probability: float | None = None
    forecast_condition: str | None = None
    roof_state: str | None = None
    is_missing: bool = False

    def __post_init__(self) -> None:
        for name in (
            "as_of_timestamp",
            "kickoff_timestamp",
            "forecast_retrieved_at",
        ):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware.")

        if self.as_of_timestamp >= self.kickoff_timestamp:
            raise ValueError("as_of_timestamp must be before kickoff_timestamp.")

        if self.forecast_retrieved_at > self.as_of_timestamp:
            raise ValueError(
                "forecast_retrieved_at must not be later than as_of_timestamp."
            )

        if not self.game_id.strip():
            raise ValueError("game_id must not be empty.")
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty.")

        if (
            self.forecast_wind_mph is not None
            and self.forecast_wind_mph < 0.0
        ):
            raise ValueError("forecast_wind_mph must not be negative.")

        if self.forecast_precip_probability is not None and not (
            0.0 <= self.forecast_precip_probability <= 1.0
        ):
            raise ValueError(
                "forecast_precip_probability must be between 0 and 1."
            )

    @property
    def forecast_age_hours(self) -> float:
        delta = self.as_of_timestamp - self.forecast_retrieved_at
        return delta.total_seconds() / 3600.0

    @property
    def hours_before_kickoff(self) -> float:
        delta = self.kickoff_timestamp - self.as_of_timestamp
        return delta.total_seconds() / 3600.0


def build_prediction_time_weather_frame(
    snapshots: Iterable[PredictionTimeWeatherSnapshot],
) -> pl.DataFrame:
    rows = []
    for snapshot in snapshots:
        row = asdict(snapshot)
        row["forecast_age_hours"] = snapshot.forecast_age_hours
        row["hours_before_kickoff"] = snapshot.hours_before_kickoff
        rows.append(row)

    if not rows:
        return pl.DataFrame(
            schema={
                "game_id": pl.String,
                "as_of_timestamp": pl.Datetime(time_zone="UTC"),
                "kickoff_timestamp": pl.Datetime(time_zone="UTC"),
                "forecast_retrieved_at": pl.Datetime(time_zone="UTC"),
                "source_id": pl.String,
                "forecast_temperature_f": pl.Float64,
                "forecast_wind_mph": pl.Float64,
                "forecast_precip_probability": pl.Float64,
                "forecast_condition": pl.String,
                "roof_state": pl.String,
                "is_missing": pl.Boolean,
                "forecast_age_hours": pl.Float64,
                "hours_before_kickoff": pl.Float64,
            }
        )

    frame = pl.DataFrame(rows)

    timestamp_columns = (
        "as_of_timestamp",
        "kickoff_timestamp",
        "forecast_retrieved_at",
    )
    for column in timestamp_columns:
        if frame[column].dtype.time_zone is None:
            frame = frame.with_columns(
                pl.col(column)
                .dt.replace_time_zone("UTC")
                .alias(column)
            )

    return frame
