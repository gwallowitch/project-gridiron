"""Validation for rest differential features."""

from __future__ import annotations

import polars as pl

REQUIRED_REST_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
        "home_rest_days",
        "away_rest_days",
        "rest_advantage",
    }
)


def validate_rest_features(frame: pl.DataFrame) -> None:
    """Raise when a rest feature dataset is unusable."""
    missing = REQUIRED_REST_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Rest features are missing columns: {missing_text}"
        )

    if frame.height == 0:
        raise ValueError("Rest feature dataset contains no games.")

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Rest features contain duplicate game rows.")

    if any(frame.null_count().row(0)):
        raise ValueError("Rest features contain null values.")
    if frame.filter(
        (pl.col("home_rest_days") <= 0)
        | (pl.col("away_rest_days") <= 0)
    ).height:
        raise ValueError("Rest days must be positive.")

    invalid_advantage = frame.filter(
        pl.col("rest_advantage")
        != (
            pl.col("home_rest_days")
            - pl.col("away_rest_days")
        )
    )
    if invalid_advantage.height:
        raise ValueError("Rest advantage does not match rest-day inputs.")
