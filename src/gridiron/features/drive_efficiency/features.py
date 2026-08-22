"""Leakage-safe pregame drive-efficiency features."""

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
    "fixed_drive",
    "fixed_drive_result",
    "epa",
}


_SCORING_RESULTS = {"Touchdown", "Field goal"}


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


def _drive_rows(pbp: pl.DataFrame) -> pl.DataFrame:
    """Collapse nflverse play-by-play to one row per offensive drive.

    nflfastR recommends fixed_drive/fixed_drive_result rather than the raw
    NFL drive field. Drive EPA is the sum of available play EPA on the drive.
    """
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    eligible = pbp.filter(
        pl.col("fixed_drive").is_not_null()
        & pl.col("posteam").is_not_null()
        & pl.col("defteam").is_not_null()
    )

    return (
        eligible.group_by(
            [
                "game_id",
                "season",
                "week",
                "posteam",
                "defteam",
                "fixed_drive",
            ]
        )
        .agg(
            pl.col("epa").drop_nulls().sum().alias("drive_epa"),
            pl.col("epa").is_not_null().sum().alias("drive_plays"),
            pl.col("fixed_drive_result")
            .drop_nulls()
            .last()
            .alias("drive_result"),
        )
        .filter(pl.col("drive_plays") > 0)
        .with_columns(
            pl.col("drive_result")
            .is_in(list(_SCORING_RESULTS))
            .cast(pl.Float64)
            .alias("drive_scored"),
            (pl.col("drive_result") == "Touchdown")
            .cast(pl.Float64)
            .alias("drive_touchdown"),
        )
    )


def _weekly_offense(drives: pl.DataFrame) -> pl.DataFrame:
    return (
        drives.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_drives"),
            pl.col("drive_epa").mean().alias("off_epa_per_drive"),
            pl.col("drive_scored").mean().alias("off_scoring_drive_rate"),
            pl.col("drive_touchdown").mean().alias("off_td_drive_rate"),
            pl.col("drive_plays").mean().alias("off_plays_per_drive"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(drives: pl.DataFrame) -> pl.DataFrame:
    return (
        drives.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_drives"),
            pl.col("drive_epa").mean().alias("def_epa_allowed_per_drive"),
            pl.col("drive_scored")
            .mean()
            .alias("def_scoring_drive_rate_allowed"),
            pl.col("drive_touchdown")
            .mean()
            .alias("def_td_drive_rate_allowed"),
            pl.col("drive_plays").mean().alias("def_plays_per_drive_allowed"),
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
    """Use only same-season weeks strictly earlier than the target game."""
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

    metric_columns = [
        column
        for column in weekly.columns
        if column not in {"season", "week", "team"}
    ]

    rolled = history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        *[
            (
                pl.col(column).sum()
                if column.endswith("_drives")
                else pl.col(column).mean()
            ).alias(column)
            for column in metric_columns
        ],
        pl.col("week_history").n_unique().alias("drive_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("drive_history_weeks").fill_null(0),
            (
                pl.col("drive_history_weeks").fill_null(0) > 0
            ).alias("drive_efficiency_known"),
        )
    )


def build_drive_efficiency_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame drive-efficiency features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    drives = _drive_rows(pbp)
    offense = _weekly_offense(drives)
    defense = _weekly_defense(drives)
    weekly = offense.join(
        defense,
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )

    team = _pregame_team_features(_schedule_teams(schedule), weekly)
    metric_columns = [
        column
        for column in team.columns
        if column not in {"game_id", "season", "week", "team", "side"}
    ]

    home = team.filter(pl.col("side") == "home").select(
        "game_id",
        *[
            pl.col(column).alias(f"home_{column}")
            for column in metric_columns
        ],
    )
    away = team.filter(pl.col("side") == "away").select(
        "game_id",
        *[
            pl.col(column).alias(f"away_{column}")
            for column in metric_columns
        ],
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
                pl.col("home_off_epa_per_drive")
                - pl.col("away_off_epa_per_drive")
            ).alias("drive_off_epa_difference"),
            (
                pl.col("away_def_epa_allowed_per_drive")
                - pl.col("home_def_epa_allowed_per_drive")
            ).alias("drive_def_epa_difference"),
            (
                pl.col("home_off_scoring_drive_rate")
                - pl.col("away_off_scoring_drive_rate")
            ).alias("scoring_drive_rate_difference"),
            (
                pl.col("home_off_td_drive_rate")
                - pl.col("away_off_td_drive_rate")
            ).alias("td_drive_rate_difference"),
            (
                pl.col("home_off_plays_per_drive")
                - pl.col("away_off_plays_per_drive")
            ).alias("plays_per_drive_difference"),
        )
    )
