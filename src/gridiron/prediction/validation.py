"""Validation for persisted game predictions."""

from __future__ import annotations

import math

import polars as pl

_REQUIRED_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "away_team",
        "home_team",
        "away_pgr",
        "home_pgr",
        "rating_difference",
        "expected_home_margin",
        "home_win_probability",
        "away_win_probability",
        "predicted_winner",
        "confidence",
        "model_version",
    }
)


def validate_predictions(frame: pl.DataFrame) -> None:
    """Validate prediction schema and mathematical invariants."""
    missing = _REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Predictions are missing required columns: {missing_text}")
    if frame.height == 0:
        raise ValueError("Predictions contain no rows.")
    if frame.select("game_id").n_unique() != frame.height:
        raise ValueError("Predictions contain duplicate game rows.")
    if frame.null_count().sum_horizontal().item() > 0:
        raise ValueError("Predictions contain null values.")

    for column in (
        "away_pgr",
        "home_pgr",
        "rating_difference",
        "expected_home_margin",
        "home_win_probability",
        "away_win_probability",
    ):
        if not all(math.isfinite(value) for value in frame[column].to_list()):
            raise ValueError(f"Prediction column contains non-finite values: {column}")

    invalid_probability = frame.filter(
        (pl.col("home_win_probability") < 0)
        | (pl.col("home_win_probability") > 1)
        | (pl.col("away_win_probability") < 0)
        | (pl.col("away_win_probability") > 1)
    )
    if invalid_probability.height:
        raise ValueError("Prediction probabilities must be between 0 and 1.")

    probability_error = frame.filter(
        (
            pl.col("home_win_probability")
            + pl.col("away_win_probability")
            - 1.0
        ).abs()
        > 1e-9
    )
    if probability_error.height:
        raise ValueError("Home and away probabilities must sum to 1.0.")

    if not set(frame["confidence"].unique()).issubset({"low", "medium", "high"}):
        raise ValueError("Predictions contain an invalid confidence tier.")
