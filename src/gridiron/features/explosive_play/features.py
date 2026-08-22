"""Step 86A — leakage-safe rolling explosive-play features."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
}

_REQUIRED_PBP = {
    "game_id",
    "posteam",
    "yards_gained",
    "pass_attempt",
    "rush_attempt",
}


def _require(
    frame: pl.DataFrame,
    required: set[str],
    label: str,
) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _team_game_explosives(pbp: pl.DataFrame) -> pl.DataFrame:
    """Aggregate offensive explosive-play rates by team and game."""
    _require(pbp, _REQUIRED_PBP, "PBP")

    offense = pbp.filter(
        pl.col("posteam").is_not_null()
        & pl.col("yards_gained").is_not_null()
        & (
            (pl.col("pass_attempt") == 1.0)
            | (pl.col("rush_attempt") == 1.0)
        )
    ).with_columns(
        (
            (pl.col("pass_attempt") == 1.0)
            & (pl.col("yards_gained") >= 20.0)
        ).cast(pl.Float64).alias("explosive_pass"),
        (
            (pl.col("rush_attempt") == 1.0)
            & (pl.col("yards_gained") >= 10.0)
        ).cast(pl.Float64).alias("explosive_rush"),
    )

    return (
        offense.group_by(
            "game_id",
            pl.col("posteam").alias("team"),
        )
        .agg(
            pl.col("pass_attempt").sum().alias("pass_attempts"),
            pl.col("rush_attempt").sum().alias("rush_attempts"),
            pl.col("explosive_pass").sum().alias("explosive_passes"),
            pl.col("explosive_rush").sum().alias("explosive_rushes"),
        )
        .with_columns(
            pl.when(pl.col("pass_attempts") > 0)
            .then(
                pl.col("explosive_passes")
                / pl.col("pass_attempts")
            )
            .otherwise(None)
            .alias("explosive_pass_rate"),
            pl.when(pl.col("rush_attempts") > 0)
            .then(
                pl.col("explosive_rushes")
                / pl.col("rush_attempts")
            )
            .otherwise(None)
            .alias("explosive_rush_rate"),
            (
                (pl.col("explosive_passes") + pl.col("explosive_rushes"))
                / (pl.col("pass_attempts") + pl.col("rush_attempts"))
            ).alias("explosive_play_rate"),
        )
    )


def build_explosive_play_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
    *,
    rolling_games: int = 4,
) -> pl.DataFrame:
    """Build prior-game rolling explosive-play rates."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    team_game = _team_game_explosives(pbp)

    long_schedule = pl.concat(
        [
            schedule.select(
                "game_id",
                "season",
                "week",
                pl.col("home_team").alias("team"),
                pl.lit("home").alias("side"),
            ),
            schedule.select(
                "game_id",
                "season",
                "week",
                pl.col("away_team").alias("team"),
                pl.lit("away").alias("side"),
            ),
        ]
    )

    history = (
        long_schedule.join(
            team_game,
            on=["game_id", "team"],
            how="left",
        )
        .sort(["team", "season", "week", "game_id"])
        .with_columns(
            pl.col("explosive_pass_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_explosive_pass_rate"),

            pl.col("explosive_rush_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_explosive_rush_rate"),

            pl.col("explosive_play_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_explosive_play_rate"),

            pl.col("explosive_play_rate")
            .shift(1)
            .is_not_null()
            .over(["team", "season"])
            .alias("explosive_play_known"),
        )
    )

    home = (
        history.filter(pl.col("side") == "home")
        .select(
            "game_id",
            pl.col("pregame_explosive_pass_rate")
            .alias("home_explosive_pass_rate"),
            pl.col("pregame_explosive_rush_rate")
            .alias("home_explosive_rush_rate"),
            pl.col("pregame_explosive_play_rate")
            .alias("home_explosive_play_rate"),
            pl.col("explosive_play_known")
            .alias("home_explosive_play_known"),
        )
    )

    away = (
        history.filter(pl.col("side") == "away")
        .select(
            "game_id",
            pl.col("pregame_explosive_pass_rate")
            .alias("away_explosive_pass_rate"),
            pl.col("pregame_explosive_rush_rate")
            .alias("away_explosive_rush_rate"),
            pl.col("pregame_explosive_play_rate")
            .alias("away_explosive_play_rate"),
            pl.col("explosive_play_known")
            .alias("away_explosive_play_known"),
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
                pl.col("home_explosive_pass_rate")
                - pl.col("away_explosive_pass_rate")
            ).alias("explosive_pass_rate_advantage"),
            (
                pl.col("home_explosive_rush_rate")
                - pl.col("away_explosive_rush_rate")
            ).alias("explosive_rush_rate_advantage"),
            (
                pl.col("home_explosive_play_rate")
                - pl.col("away_explosive_play_rate")
            ).alias("explosive_play_rate_advantage"),
        )
    )
