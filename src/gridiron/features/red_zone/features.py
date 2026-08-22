"""Leakage-safe pregame red-zone efficiency features."""

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
    "yardline_100",
    "epa",
    "success",
    "touchdown",
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


def _red_zone_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return offensive plays snapped at or inside the opponent 20."""
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    return (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("yardline_100").is_not_null()
            & (pl.col("yardline_100") <= 20)
            & (pl.col("yardline_100") > 0)
            & pl.col("epa").is_not_null()
        )
        .with_columns(
            pl.col("success")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_success"),
            pl.col("touchdown")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_touchdown"),
        )
    )


def _weekly_offense(red_zone: pl.DataFrame) -> pl.DataFrame:
    return (
        red_zone.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_red_zone_plays"),
            pl.col("epa").mean().alias("off_red_zone_epa_per_play"),
            pl.col("_success").mean().alias("off_red_zone_success_rate"),
            pl.col("_touchdown").mean().alias("off_red_zone_td_play_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(red_zone: pl.DataFrame) -> pl.DataFrame:
    return (
        red_zone.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_red_zone_plays"),
            pl.col("epa").mean().alias("def_red_zone_epa_allowed_per_play"),
            pl.col("_success").mean().alias("def_red_zone_success_rate_allowed"),
            pl.col("_touchdown").mean().alias("def_red_zone_td_play_rate_allowed"),
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
                if column.endswith("_plays")
                else pl.col(column).mean()
            ).alias(column)
            for column in metric_columns
        ],
        pl.col("week_history")
        .n_unique()
        .alias("red_zone_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("red_zone_history_weeks").fill_null(0),
            (
                pl.col("red_zone_history_weeks").fill_null(0) > 0
            ).alias("red_zone_known"),
        )
    )


def build_red_zone_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build game-level pregame red-zone features.

    Only same-season weeks strictly earlier than the prediction week are used.
    """
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    red_zone = _red_zone_plays(pbp)
    offense = _weekly_offense(red_zone)
    defense = _weekly_defense(red_zone)
    weekly = offense.join(
        defense,
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )

    schedule_teams = _schedule_teams(schedule)
    team = _pregame_team_features(schedule_teams, weekly)

    metric_columns = [
        column
        for column in team.columns
        if column
        not in {"game_id", "season", "week", "team", "side"}
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
                pl.col("home_off_red_zone_epa_per_play")
                - pl.col("away_off_red_zone_epa_per_play")
            ).alias("red_zone_off_epa_difference"),
            (
                pl.col("away_def_red_zone_epa_allowed_per_play")
                - pl.col("home_def_red_zone_epa_allowed_per_play")
            ).alias("red_zone_def_epa_difference"),
            (
                pl.col("home_off_red_zone_success_rate")
                - pl.col("away_off_red_zone_success_rate")
            ).alias("red_zone_success_difference"),
            (
                pl.col("home_off_red_zone_td_play_rate")
                - pl.col("away_off_red_zone_td_play_rate")
            ).alias("red_zone_td_rate_difference"),
        )
    )
