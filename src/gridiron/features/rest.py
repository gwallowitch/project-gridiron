"""Rest differential feature engineering for Project Gridiron."""

from __future__ import annotations

import polars as pl

DEFAULT_REST_DAYS = 7
REQUIRED_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
    }
)


def build_rest_features(schedule: pl.DataFrame) -> pl.DataFrame:
    """Build one row of rest features for every scheduled game."""
    missing = REQUIRED_COLUMNS.difference(schedule.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Schedule is missing required columns: {missing_text}"
        )

    if schedule.height == 0:
        raise ValueError("Schedule contains no games.")

    gameday_dtype = schedule.schema["gameday"]

    if gameday_dtype == pl.String:
        prepared = schedule.with_columns(
            pl.col("gameday").str.to_date(strict=False)
        )
    else:
        prepared = schedule.with_columns(
            pl.col("gameday").cast(pl.Date, strict=False)
        )

    if prepared["gameday"].null_count():
        raise ValueError("Schedule contains invalid or missing game dates.")

    team_games = pl.concat(
        [
            prepared.select(
                "game_id",
                "season",
                "week",
                "gameday",
                pl.col("home_team").alias("team"),
            ),
            prepared.select(
                "game_id",
                "season",
                "week",
                "gameday",
                pl.col("away_team").alias("team"),
            ),
        ]
    ).sort(["season", "team", "gameday", "game_id"])

    team_games = (
        team_games.with_columns(
            pl.col("gameday")
            .shift(1)
            .over(["season", "team"])
            .alias("previous_gameday")
        )
        .with_columns(
            pl.when(pl.col("previous_gameday").is_null())
            .then(pl.lit(DEFAULT_REST_DAYS))
            .otherwise(
                (
                    pl.col("gameday") - pl.col("previous_gameday")
                ).dt.total_days()
            )
            .cast(pl.Int32)
            .alias("rest_days")
        )
    )

    if team_games.filter(pl.col("rest_days") <= 0).height:
        raise ValueError(
            "Schedule contains non-positive rest intervals for a team."
        )

    home_lookup = (
        team_games.join(
            prepared.select("game_id", "home_team"),
            on="game_id",
            how="inner",
        )
        .filter(pl.col("team") == pl.col("home_team"))
        .select(
            "game_id",
            pl.col("rest_days").alias("home_rest_days"),
        )
    )
    away_lookup = (
        team_games.join(
            prepared.select("game_id", "away_team"),
            on="game_id",
            how="inner",
        )
        .filter(pl.col("team") == pl.col("away_team"))
        .select(
            "game_id",
            pl.col("rest_days").alias("away_rest_days"),
        )
    )

    result = (
        prepared.select(
            "game_id",
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
        )
        .join(home_lookup, on="game_id", how="left")
        .join(away_lookup, on="game_id", how="left")
        .with_columns(
            (
                pl.col("home_rest_days") - pl.col("away_rest_days")
            ).alias("rest_advantage")
        )
        .sort(["season", "week", "game_id"])
    )

    if any(result.null_count().row(0)):
        raise ValueError("Rest features contain null values.")

    return result
