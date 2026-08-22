"""Leakage-safe pregame fourth-down efficiency features."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {
    "game_id", "season", "week", "home_team", "away_team",
}
_REQUIRED_PBP = {
    "game_id", "season", "week", "posteam", "defteam",
    "down", "ydstogo", "yards_gained", "play_type", "epa",
}
_ELIGIBLE_PLAY_TYPES = {"run", "pass"}
_SHORT_YARDS = 2.0


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: " + ", ".join(sorted(missing))
        )


def _fourth_down_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return qualifying fourth-down offensive scrimmage attempts."""
    _require(pbp, _REQUIRED_PBP, "Play-by-play")
    return (
        pbp.filter(
            (pl.col("down") == 4)
            & pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
            & pl.col("ydstogo").is_not_null()
            & pl.col("yards_gained").is_not_null()
        )
        .with_columns(
            (
                pl.col("yards_gained").cast(pl.Float64)
                >= pl.col("ydstogo").cast(pl.Float64)
            ).cast(pl.Float64).alias("_converted"),
            (
                pl.col("ydstogo").cast(pl.Float64) <= _SHORT_YARDS
            ).alias("_short_yardage"),
        )
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_fourth_down_attempts"),
            pl.col("epa").cast(pl.Float64, strict=False).drop_nulls().mean()
            .alias("off_fourth_down_epa"),
            pl.col("_converted").mean().alias("off_fourth_down_conversion_rate"),
            pl.col("_short_yardage").sum().alias("off_fourth_short_attempts"),
            pl.col("_converted").filter(pl.col("_short_yardage")).mean()
            .alias("off_fourth_short_conversion_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_fourth_down_attempts_faced"),
            pl.col("epa").cast(pl.Float64, strict=False).drop_nulls().mean()
            .alias("def_fourth_down_epa_allowed"),
            pl.col("_converted").mean()
            .alias("def_fourth_down_conversion_rate_allowed"),
            pl.col("_short_yardage").sum().alias("def_fourth_short_attempts_faced"),
            pl.col("_converted").filter(pl.col("_short_yardage")).mean()
            .alias("def_fourth_short_conversion_rate_allowed"),
        )
        .rename({"defteam": "team"})
    )


def _schedule_teams(schedule: pl.DataFrame) -> pl.DataFrame:
    return pl.concat(
        [
            schedule.select(
                "game_id", "season", "week",
                pl.col("home_team").alias("team"),
                pl.lit("home").alias("side"),
            ),
            schedule.select(
                "game_id", "season", "week",
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
            weekly, on=["season", "team"], how="left", suffix="_history"
        )
        .filter(
            pl.col("week_history").is_not_null()
            & (pl.col("week_history") < pl.col("week"))
        )
    )
    count_columns = {
        "off_fourth_down_attempts",
        "off_fourth_short_attempts",
        "def_fourth_down_attempts_faced",
        "def_fourth_short_attempts_faced",
    }
    metric_columns = [
        c for c in weekly.columns if c not in {"season", "week", "team"}
    ]
    rolled = history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        *[
            (pl.col(c).sum() if c in count_columns else pl.col(c).mean()).alias(c)
            for c in metric_columns
        ],
        pl.col("week_history").n_unique().alias("fourth_down_history_weeks"),
    )
    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("fourth_down_history_weeks").fill_null(0),
            (pl.col("fourth_down_history_weeks").fill_null(0) > 0)
            .alias("fourth_down_known"),
        )
    )


def build_fourth_down_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame fourth-down matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    plays = _fourth_down_plays(pbp)
    weekly = _weekly_offense(plays).join(
        _weekly_defense(plays),
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )
    team = _pregame_team_features(_schedule_teams(schedule), weekly)
    metric_columns = [
        c for c in team.columns
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
        schedule.select("game_id", "season", "week", "home_team", "away_team")
        .join(home, on="game_id", how="left")
        .join(away, on="game_id", how="left")
        .with_columns(
            (
                pl.col("home_off_fourth_down_epa")
                - pl.col("away_off_fourth_down_epa")
            ).alias("fourth_down_off_epa_difference"),
            (
                pl.col("away_def_fourth_down_epa_allowed")
                - pl.col("home_def_fourth_down_epa_allowed")
            ).alias("fourth_down_def_epa_difference"),
            (
                pl.col("home_off_fourth_down_conversion_rate")
                - pl.col("away_off_fourth_down_conversion_rate")
            ).alias("fourth_down_conversion_difference"),
            (
                pl.col("away_def_fourth_down_conversion_rate_allowed")
                - pl.col("home_def_fourth_down_conversion_rate_allowed")
            ).alias("fourth_down_stop_difference"),
            (
                pl.col("home_off_fourth_short_conversion_rate")
                - pl.col("away_off_fourth_short_conversion_rate")
            ).alias("fourth_short_conversion_difference"),
        )
    )
