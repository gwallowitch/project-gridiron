"""Quarterback feature engineering for scheduled games."""

from __future__ import annotations

import polars as pl

from gridiron.features.qb.models import (
    DEFAULT_QB_NAME,
    DEFAULT_QB_RATING,
    SCHEDULE_COLUMNS,
)


def build_qb_features(
    schedule: pl.DataFrame,
    starters: pl.DataFrame,
    ratings: pl.DataFrame,
) -> pl.DataFrame:
    """Build quarterback context for every scheduled game."""
    missing = SCHEDULE_COLUMNS.difference(schedule.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Schedule is missing required columns: {missing_text}"
        )
    if schedule.height == 0:
        raise ValueError("Schedule contains no games.")

    home = _team_qb_lookup(
        schedule=schedule,
        starters=starters,
        ratings=ratings,
        team_column="home_team",
        prefix="home",
    )
    away = _team_qb_lookup(
        schedule=schedule,
        starters=starters,
        ratings=ratings,
        team_column="away_team",
        prefix="away",
    )

    result = (
        schedule.select(
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
        )
        .join(home, on="game_id", how="left", validate="1:1")
        .join(away, on="game_id", how="left", validate="1:1")
        .with_columns(
            (
                pl.col("home_qb_rating")
                - pl.col("away_qb_rating")
            ).alias("qb_rating_difference"),
            (
                pl.col("home_qb") != DEFAULT_QB_NAME
            ).alias("home_qb_known"),
            (
                pl.col("away_qb") != DEFAULT_QB_NAME
            ).alias("away_qb_known"),
        )
        .sort(["season", "week", "game_id"])
    )

    if any(result.null_count().row(0)):
        raise ValueError("QB features contain null values.")
    return result


def _team_qb_lookup(
    *,
    schedule: pl.DataFrame,
    starters: pl.DataFrame,
    ratings: pl.DataFrame,
    team_column: str,
    prefix: str,
) -> pl.DataFrame:
    game_teams = schedule.select(
        "game_id",
        "season",
        "week",
        pl.col(team_column).alias("team"),
    )

    lookup = (
        game_teams.join(
            starters,
            on=["season", "week", "team"],
            how="left",
            validate="m:1",
        )
        .with_columns(
            pl.col("qb_name").fill_null(DEFAULT_QB_NAME)
        )
        .join(
            ratings,
            on="qb_name",
            how="left",
            validate="m:1",
        )
        .with_columns(
            pl.col("rating").fill_null(DEFAULT_QB_RATING)
        )
        .select(
            "game_id",
            pl.col("qb_name").alias(f"{prefix}_qb"),
            pl.col("rating").alias(f"{prefix}_qb_rating"),
        )
    )
    return lookup
