"""Leakage-safe pregame pressure and pass-protection features."""

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
    "qb_hit",
    "sack",
    "epa",
}

_ELIGIBLE_PLAY_TYPES = {"pass"}


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


def _dropbacks(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return pass plays with conservative pressure-proxy flags.

    nflverse play-by-play exposes QB hits and sacks consistently enough for
    historical research. A pressure event is defined as qb_hit OR sack.
    This intentionally does not pretend that unobserved hurries are available.
    """
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    return (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
        )
        .with_columns(
            pl.col("qb_hit")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .gt(0)
            .alias("_qb_hit"),
            pl.col("sack")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .gt(0)
            .alias("_sack"),
        )
        .with_columns(
            (pl.col("_qb_hit") | pl.col("_sack")).alias("_pressure"),
        )
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_dropbacks"),
            pl.col("_pressure").sum().alias("off_pressure_events"),
            pl.col("_qb_hit").sum().alias("off_qb_hits_allowed"),
            pl.col("_sack").sum().alias("off_sacks_allowed"),
            pl.col("_pressure")
            .cast(pl.Float64)
            .mean()
            .alias("off_pressure_allowed_rate"),
            (
                pl.col("_pressure").not_().cast(pl.Float64).mean()
            ).alias("off_clean_dropback_rate"),
            pl.col("epa")
            .cast(pl.Float64, strict=False)
            .filter(pl.col("_pressure"))
            .drop_nulls()
            .mean()
            .alias("off_pressured_epa"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_dropbacks_faced"),
            pl.col("_pressure").sum().alias("def_pressure_events"),
            pl.col("_qb_hit").sum().alias("def_qb_hits"),
            pl.col("_sack").sum().alias("def_sacks"),
            pl.col("_pressure")
            .cast(pl.Float64)
            .mean()
            .alias("def_pressure_rate"),
            pl.col("epa")
            .cast(pl.Float64, strict=False)
            .filter(pl.col("_pressure"))
            .drop_nulls()
            .mean()
            .alias("def_pressured_epa_allowed"),
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
    """Roll same-season history using only weeks before the target game."""
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
        "off_dropbacks",
        "off_pressure_events",
        "off_qb_hits_allowed",
        "off_sacks_allowed",
        "def_dropbacks_faced",
        "def_pressure_events",
        "def_qb_hits",
        "def_sacks",
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
        pl.col("week_history").n_unique().alias("pressure_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("pressure_history_weeks").fill_null(0),
            (
                pl.col("pressure_history_weeks").fill_null(0) > 0
            ).alias("pressure_known"),
        )
    )


def build_pressure_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame pressure/pass-protection matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    plays = _dropbacks(pbp)
    weekly = _weekly_offense(plays).join(
        _weekly_defense(plays),
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )

    team = _pregame_team_features(_schedule_teams(schedule), weekly)
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
                pl.col("away_off_pressure_allowed_rate")
                - pl.col("home_off_pressure_allowed_rate")
            ).alias("pass_protection_advantage"),
            (
                pl.col("home_def_pressure_rate")
                - pl.col("away_def_pressure_rate")
            ).alias("pressure_creation_advantage"),
            (
                pl.col("home_off_clean_dropback_rate")
                - pl.col("away_off_clean_dropback_rate")
            ).alias("clean_dropback_advantage"),
            (
                pl.col("home_off_pressured_epa")
                - pl.col("away_off_pressured_epa")
            ).alias("pressured_off_epa_difference"),
            (
                pl.col("away_def_pressured_epa_allowed")
                - pl.col("home_def_pressured_epa_allowed")
            ).alias("pressured_def_epa_advantage"),
        )
    )
