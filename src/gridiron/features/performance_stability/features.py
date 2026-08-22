"""Step 84A — leakage-safe rolling performance stability features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
}


def _require(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Schedule is missing required columns: "
            + ", ".join(sorted(missing))
        )


def build_performance_stability_features(
    schedule: pl.DataFrame,
    *,
    rolling_games: int = 4,
    close_game_margin: float = 7.0,
) -> pl.DataFrame:
    """Build pregame team stability features from prior games only.

    Features:
    - rolling mean point differential;
    - rolling standard deviation of point differential;
    - rolling mean absolute point differential;
    - rolling close-game rate (final margin <= close_game_margin).

    Current-game results are shifted out before rolling calculations.
    """
    _require(schedule)

    home_rows = schedule.select(
        "game_id",
        "season",
        "week",
        pl.col("home_team").alias("team"),
        pl.lit("home").alias("side"),
        (pl.col("home_score") - pl.col("away_score"))
        .cast(pl.Float64)
        .alias("point_differential"),
    )

    away_rows = schedule.select(
        "game_id",
        "season",
        "week",
        pl.col("away_team").alias("team"),
        pl.lit("away").alias("side"),
        (pl.col("away_score") - pl.col("home_score"))
        .cast(pl.Float64)
        .alias("point_differential"),
    )

    history = (
        pl.concat([home_rows, away_rows])
        .with_columns(
            pl.col("point_differential")
            .abs()
            .alias("absolute_point_differential"),
            (pl.col("point_differential").abs() <= close_game_margin)
            .cast(pl.Float64)
            .alias("close_game"),
        )
        .sort(["team", "season", "week", "game_id"])
        .with_columns(
            pl.col("point_differential")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_mean_point_differential"),
            pl.col("point_differential")
            .shift(1)
            .rolling_std(
                window_size=rolling_games,
                min_samples=2,
            )
            .over(["team", "season"])
            .alias("pregame_point_differential_std"),
            pl.col("absolute_point_differential")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_mean_absolute_margin"),
            pl.col("close_game")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_close_game_rate"),
            pl.col("point_differential")
            .shift(1)
            .is_not_null()
            .over(["team", "season"])
            .alias("performance_stability_known"),
        )
    )

    home = (
        history.filter(pl.col("side") == "home")
        .select(
            "game_id",
            pl.col("pregame_mean_point_differential")
            .alias("home_mean_point_differential"),
            pl.col("pregame_point_differential_std")
            .alias("home_point_differential_std"),
            pl.col("pregame_mean_absolute_margin")
            .alias("home_mean_absolute_margin"),
            pl.col("pregame_close_game_rate")
            .alias("home_close_game_rate"),
            pl.col("performance_stability_known")
            .alias("home_performance_stability_known"),
        )
    )

    away = (
        history.filter(pl.col("side") == "away")
        .select(
            "game_id",
            pl.col("pregame_mean_point_differential")
            .alias("away_mean_point_differential"),
            pl.col("pregame_point_differential_std")
            .alias("away_point_differential_std"),
            pl.col("pregame_mean_absolute_margin")
            .alias("away_mean_absolute_margin"),
            pl.col("pregame_close_game_rate")
            .alias("away_close_game_rate"),
            pl.col("performance_stability_known")
            .alias("away_performance_stability_known"),
        )
    )

    return (
        schedule.select(
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
        )
        .join(home, on="game_id", how="left")
        .join(away, on="game_id", how="left")
        .with_columns(
            (
                pl.col("away_point_differential_std")
                - pl.col("home_point_differential_std")
            ).alias("stability_advantage"),
            (
                pl.col("home_mean_point_differential")
                - pl.col("away_mean_point_differential")
            ).alias("recent_margin_advantage"),
            (
                pl.col("home_close_game_rate")
                - pl.col("away_close_game_rate")
            ).alias("close_game_experience_advantage"),
        )
    )
