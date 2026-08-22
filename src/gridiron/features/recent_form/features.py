"""Leakage-safe pregame recent-form and trend features."""

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
    "epa",
}

_ELIGIBLE_PLAY_TYPES = {"run", "pass"}
_RECENT_WEEKS = 3


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
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
            & pl.col("epa").is_not_null()
        )
        .with_columns(
            pl.col("epa").cast(pl.Float64, strict=False).alias("_epa"),
        )
        .filter(pl.col("_epa").is_not_null())
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_plays"),
            pl.col("_epa").mean().alias("off_epa_per_play"),
            (pl.col("_epa") > 0).cast(pl.Float64).mean().alias("off_success_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_plays_faced"),
            pl.col("_epa").mean().alias("def_epa_allowed_per_play"),
            (pl.col("_epa") > 0).cast(pl.Float64).mean().alias(
                "def_success_rate_allowed"
            ),
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


def _aggregate_history(
    schedule_teams: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
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
        .with_columns(
            (
                pl.col("week_history")
                >= (pl.col("week") - _RECENT_WEEKS)
            ).alias("_is_recent")
        )
    )

    return history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        pl.col("off_plays").sum().alias("season_off_plays"),
        pl.col("def_plays_faced").sum().alias("season_def_plays_faced"),
        pl.col("off_epa_per_play").mean().alias("season_off_epa"),
        pl.col("def_epa_allowed_per_play").mean().alias("season_def_epa_allowed"),
        pl.col("off_success_rate").mean().alias("season_off_success"),
        pl.col("def_success_rate_allowed").mean().alias(
            "season_def_success_allowed"
        ),
        pl.col("off_epa_per_play")
        .filter(pl.col("_is_recent"))
        .mean()
        .alias("recent_off_epa"),
        pl.col("def_epa_allowed_per_play")
        .filter(pl.col("_is_recent"))
        .mean()
        .alias("recent_def_epa_allowed"),
        pl.col("off_success_rate")
        .filter(pl.col("_is_recent"))
        .mean()
        .alias("recent_off_success"),
        pl.col("def_success_rate_allowed")
        .filter(pl.col("_is_recent"))
        .mean()
        .alias("recent_def_success_allowed"),
        pl.col("week_history")
        .filter(pl.col("_is_recent"))
        .n_unique()
        .alias("recent_form_weeks"),
        pl.col("week_history").n_unique().alias("season_form_weeks"),
    )


def _pregame_team_features(
    schedule_teams: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    rolled = _aggregate_history(schedule_teams, weekly)

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("recent_form_weeks").fill_null(0),
            pl.col("season_form_weeks").fill_null(0),
            (
                pl.col("recent_form_weeks").fill_null(0) >= 2
            ).alias("recent_form_known"),
        )
        .with_columns(
            (
                pl.col("recent_off_epa") - pl.col("season_off_epa")
            ).alias("off_epa_trend"),
            (
                pl.col("season_def_epa_allowed")
                - pl.col("recent_def_epa_allowed")
            ).alias("def_epa_improvement"),
            (
                pl.col("recent_off_success")
                - pl.col("season_off_success")
            ).alias("off_success_trend"),
            (
                pl.col("season_def_success_allowed")
                - pl.col("recent_def_success_allowed")
            ).alias("def_success_improvement"),
        )
    )


def build_recent_form_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame recent-vs-season form features."""
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
                pl.col("home_recent_off_epa")
                - pl.col("away_recent_off_epa")
            ).alias("recent_off_epa_difference"),
            (
                pl.col("away_recent_def_epa_allowed")
                - pl.col("home_recent_def_epa_allowed")
            ).alias("recent_def_epa_advantage"),
            (
                pl.col("home_off_epa_trend")
                - pl.col("away_off_epa_trend")
            ).alias("off_epa_trend_difference"),
            (
                pl.col("home_def_epa_improvement")
                - pl.col("away_def_epa_improvement")
            ).alias("def_epa_trend_advantage"),
            (
                pl.col("home_off_success_trend")
                - pl.col("away_off_success_trend")
            ).alias("off_success_trend_difference"),
            (
                pl.col("home_def_success_improvement")
                - pl.col("away_def_success_improvement")
            ).alias("def_success_trend_advantage"),
        )
    )
