"""Leakage-safe team pace / tempo features for Step 83A."""

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
}


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _play_flag(pbp: pl.DataFrame) -> pl.Expr:
    if "play_type" in pbp.columns:
        return (
            pl.col("play_type")
            .is_in(["run", "pass"])
            .fill_null(False)
            .cast(pl.Int64)
        )
    return pl.lit(1, dtype=pl.Int64)


def _seconds_expr(pbp: pl.DataFrame) -> pl.Expr:
    if "play_clock" in pbp.columns:
        return pl.col("play_clock").cast(pl.Float64, strict=False)

    if "seconds_to_snap" in pbp.columns:
        return pl.col("seconds_to_snap").cast(pl.Float64, strict=False)

    return pl.lit(None, dtype=pl.Float64)


def build_team_game_pace(pbp: pl.DataFrame) -> pl.DataFrame:
    """Build game-level team pace observations from play-by-play."""
    _require(pbp, _REQUIRED_PBP, "PBP")

    base = (
        pbp.filter(pl.col("posteam").is_not_null())
        .with_columns(
            _play_flag(pbp).alias("_off_play"),
            _seconds_expr(pbp).alias("_seconds_to_snap"),
        )
        .group_by("game_id", "posteam")
        .agg(
            pl.col("_off_play").sum().alias("offensive_plays"),
            pl.col("_seconds_to_snap")
            .filter(pl.col("_off_play") == 1)
            .mean()
            .alias("seconds_to_snap"),
        )
        .rename({"posteam": "team"})
    )

    return base.with_columns(
        pl.when(pl.col("offensive_plays") > 0)
        .then(60.0 / pl.col("seconds_to_snap"))
        .otherwise(None)
        .alias("tempo_index")
    )


def build_pace_tempo_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
    *,
    rolling_games: int = 4,
) -> pl.DataFrame:
    """Build pregame pace features using prior games only."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    team_game = build_team_game_pace(pbp)

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
            pl.col("offensive_plays")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_offensive_plays"),
            pl.col("seconds_to_snap")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_seconds_to_snap"),
            pl.col("tempo_index")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_tempo_index"),
            pl.col("offensive_plays")
            .shift(1)
            .is_not_null()
            .over(["team", "season"])
            .alias("pace_tempo_known"),
        )
    )

    home = (
        history.filter(pl.col("side") == "home")
        .select(
            "game_id",
            pl.col("pregame_offensive_plays")
            .alias("home_pregame_offensive_plays"),
            pl.col("pregame_seconds_to_snap")
            .alias("home_pregame_seconds_to_snap"),
            pl.col("pregame_tempo_index")
            .alias("home_pregame_tempo_index"),
            pl.col("pace_tempo_known").alias("home_pace_tempo_known"),
        )
    )

    away = (
        history.filter(pl.col("side") == "away")
        .select(
            "game_id",
            pl.col("pregame_offensive_plays")
            .alias("away_pregame_offensive_plays"),
            pl.col("pregame_seconds_to_snap")
            .alias("away_pregame_seconds_to_snap"),
            pl.col("pregame_tempo_index")
            .alias("away_pregame_tempo_index"),
            pl.col("pace_tempo_known").alias("away_pace_tempo_known"),
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
                pl.col("home_pregame_offensive_plays")
                - pl.col("away_pregame_offensive_plays")
            ).alias("pace_play_volume_advantage"),
            (
                pl.col("away_pregame_seconds_to_snap")
                - pl.col("home_pregame_seconds_to_snap")
            ).alias("pace_seconds_advantage"),
            (
                pl.col("home_pregame_tempo_index")
                - pl.col("away_pregame_tempo_index")
            ).alias("tempo_index_advantage"),
        )
    )
