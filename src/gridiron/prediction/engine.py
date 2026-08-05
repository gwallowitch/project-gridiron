"""Prediction Engine v1 mathematics."""

from __future__ import annotations

import polars as pl

from gridiron.prediction.confidence import classify_confidence
from gridiron.prediction.constants import (
    HOME_FIELD_ADVANTAGE,
    MARGIN_SCALE,
    PREDICTION_MODEL_VERSION,
    PROBABILITY_SCALE,
    RATING_CENTER,
)
from gridiron.prediction.probability import home_win_probability

_REQUIRED_SCHEDULE_COLUMNS = frozenset(
    {"game_id", "season", "week", "away_team", "home_team"}
)
_REQUIRED_PGR_COLUMNS = frozenset(
    {"season", "week", "team", "pgr_rating"}
)


def build_predictions(
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    *,
    home_field_advantage: float = HOME_FIELD_ADVANTAGE,
    probability_scale: float = PROBABILITY_SCALE,
) -> pl.DataFrame:
    """Build leak-free predictions using prior-week PGR values."""
    _validate_inputs(schedule, pgr)

    games = schedule.select(
        *[
            column
            for column in (
                "game_id",
                "season",
                "week",
                "game_type",
                "gameday",
                "away_team",
                "home_team",
            )
            if column in schedule.columns
        ]
    ).with_columns(
        (pl.col("week") - 1).clip(lower_bound=0).alias("rating_week")
    )

    home_ratings = pgr.select(
        "season",
        pl.col("week").alias("rating_week"),
        pl.col("team").alias("home_team"),
        pl.col("pgr_rating").alias("home_pgr"),
    )
    away_ratings = pgr.select(
        "season",
        pl.col("week").alias("rating_week"),
        pl.col("team").alias("away_team"),
        pl.col("pgr_rating").alias("away_pgr"),
    )

    result = (
        games.join(
            home_ratings,
            on=["season", "rating_week", "home_team"],
            how="left",
            validate="m:1",
        )
        .join(
            away_ratings,
            on=["season", "rating_week", "away_team"],
            how="left",
            validate="m:1",
        )
        .with_columns(
            pl.col("home_pgr").fill_null(RATING_CENTER),
            pl.col("away_pgr").fill_null(RATING_CENTER),
            pl.lit(home_field_advantage).alias("home_field_advantage"),
        )
        .with_columns(
            (
                pl.col("home_pgr")
                - pl.col("away_pgr")
                + pl.col("home_field_advantage")
            ).alias("rating_difference")
        )
        .with_columns(
            (
                pl.col("rating_difference") * MARGIN_SCALE
            ).alias("expected_home_margin"),
            pl.col("rating_difference")
            .map_elements(
                lambda value: home_win_probability(
                    value,
                    scale=probability_scale,
                ),
                return_dtype=pl.Float64,
            )
            .alias("home_win_probability"),
        )
        .with_columns(
            (1.0 - pl.col("home_win_probability")).alias(
                "away_win_probability"
            ),
            pl.when(pl.col("rating_difference") >= 0)
            .then(pl.col("home_team"))
            .otherwise(pl.col("away_team"))
            .alias("predicted_winner"),
            pl.col("home_win_probability")
            .map_elements(classify_confidence, return_dtype=pl.String)
            .alias("confidence"),
            pl.lit(PREDICTION_MODEL_VERSION).alias("model_version"),
        )
        .sort(["week", "game_id"])
    )

    return result


def _validate_inputs(schedule: pl.DataFrame, pgr: pl.DataFrame) -> None:
    missing_schedule = _REQUIRED_SCHEDULE_COLUMNS.difference(schedule.columns)
    if missing_schedule:
        missing = ", ".join(sorted(missing_schedule))
        raise ValueError(f"Schedule is missing required columns: {missing}")

    missing_pgr = _REQUIRED_PGR_COLUMNS.difference(pgr.columns)
    if missing_pgr:
        missing = ", ".join(sorted(missing_pgr))
        raise ValueError(f"PGR data is missing required columns: {missing}")

    if schedule.height == 0:
        raise ValueError("Schedule contains no rows.")
    if pgr.height == 0:
        raise ValueError("PGR data contains no rows.")
    if schedule.select("game_id").n_unique() != schedule.height:
        raise ValueError("Schedule contains duplicate game rows.")
