"""Leakage-safe pregame explosive-play and chunk-play features."""

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
    "season",
    "week",
    "posteam",
    "defteam",
    "play_type",
    "yards_gained",
}

_ELIGIBLE_PLAY_TYPES = {"run", "pass"}
_CHUNK_YARDS = 10.0
_EXPLOSIVE_YARDS = 20.0


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


def _eligible_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    return (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
            & pl.col("yards_gained").is_not_null()
        )
        .with_columns(
            pl.col("yards_gained")
            .cast(pl.Float64, strict=False)
            .alias("_yards"),
        )
        .filter(pl.col("_yards").is_not_null())
        .with_columns(
            (pl.col("_yards") >= _CHUNK_YARDS)
            .cast(pl.Float64)
            .alias("_chunk"),
            (pl.col("_yards") >= _EXPLOSIVE_YARDS)
            .cast(pl.Float64)
            .alias("_explosive"),
            pl.when(pl.col("_yards") >= _EXPLOSIVE_YARDS)
            .then(pl.col("_yards"))
            .otherwise(0.0)
            .alias("_explosive_yards"),
            pl.when(pl.col("_yards") > 0)
            .then(pl.col("_yards"))
            .otherwise(0.0)
            .alias("_positive_yards"),
        )
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_scrimmage_plays"),
            pl.col("_chunk").mean().alias("off_chunk_play_rate"),
            pl.col("_explosive").mean().alias("off_explosive_play_rate"),
            pl.col("_explosive_yards").sum().alias("off_explosive_yards"),
            pl.col("_positive_yards").sum().alias("off_positive_yards"),
        )
        .with_columns(
            pl.when(pl.col("off_positive_yards") > 0)
            .then(
                pl.col("off_explosive_yards")
                / pl.col("off_positive_yards")
            )
            .otherwise(None)
            .alias("off_explosive_yards_share")
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_scrimmage_plays_faced"),
            pl.col("_chunk").mean().alias("def_chunk_play_rate_allowed"),
            pl.col("_explosive").mean().alias("def_explosive_play_rate_allowed"),
            pl.col("_explosive_yards").sum().alias("def_explosive_yards_allowed"),
            pl.col("_positive_yards").sum().alias("def_positive_yards_allowed"),
        )
        .with_columns(
            pl.when(pl.col("def_positive_yards_allowed") > 0)
            .then(
                pl.col("def_explosive_yards_allowed")
                / pl.col("def_positive_yards_allowed")
            )
            .otherwise(None)
            .alias("def_explosive_yards_share_allowed")
        )
        .rename({"defteam": "team"})
    )


def _schedule_teams(schedule: pl.DataFrame) -> pl.DataFrame:
    return pl.concat(
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


def _pregame_team_features(
    schedule_teams: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    """Use only same-season weeks strictly before the target game."""
    history = (
        schedule_teams.join(
            weekly,
            on=["season", "team"],
            how="left",
            suffix="_history",
        )
        .filter(
            pl.col("week_history").is_not_null()
            & (pl.col("week_history") < pl.col("week"))
        )
    )

    count_columns = {
        "off_scrimmage_plays",
        "off_explosive_yards",
        "off_positive_yards",
        "def_scrimmage_plays_faced",
        "def_explosive_yards_allowed",
        "def_positive_yards_allowed",
    }
    metric_columns = [
        c for c in weekly.columns if c not in {"season", "week", "team"}
    ]

    rolled = history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        *[
            (
                pl.col(c).sum()
                if c in count_columns
                else pl.col(c).mean()
            ).alias(c)
            for c in metric_columns
        ],
        pl.col("week_history").n_unique().alias(
            "explosive_suppression_history_weeks"
        ),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("explosive_suppression_history_weeks").fill_null(0),
            (
                pl.col("explosive_suppression_history_weeks")
                .fill_null(0) > 0
            ).alias("explosive_suppression_known"),
        )
    )


def build_explosive_suppression_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame explosive-play matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    plays = _eligible_plays(pbp)
    weekly = _weekly_offense(plays).join(
        _weekly_defense(plays),
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )

    team = _pregame_team_features(
        _schedule_teams(schedule),
        weekly,
    )

    metric_columns = [
        c
        for c in team.columns
        if c not in {"game_id", "season", "week", "team", "side"}
    ]

    home = team.filter(pl.col("side") == "home").select(
        "game_id",
        *[pl.col(c).alias(f"home_{c}") for c in metric_columns],
    )
    away = team.filter(pl.col("side") == "away").select(
        "game_id",
        *[pl.col(c).alias(f"away_{c}") for c in metric_columns],
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
                pl.col("home_off_explosive_play_rate")
                - pl.col("away_off_explosive_play_rate")
            ).alias("explosive_off_rate_difference"),
            (
                pl.col("away_def_explosive_play_rate_allowed")
                - pl.col("home_def_explosive_play_rate_allowed")
            ).alias("explosive_suppression_advantage"),
            (
                pl.col("home_off_chunk_play_rate")
                - pl.col("away_off_chunk_play_rate")
            ).alias("chunk_off_rate_difference"),
            (
                pl.col("away_def_chunk_play_rate_allowed")
                - pl.col("home_def_chunk_play_rate_allowed")
            ).alias("chunk_suppression_advantage"),
            (
                pl.col("home_off_explosive_yards_share")
                - pl.col("away_off_explosive_yards_share")
            ).alias("explosive_yards_share_difference"),
        )
    )
