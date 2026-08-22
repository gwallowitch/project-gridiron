"""Leakage-safe pregame field-position and hidden-yards features."""

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
    "drive",
    "posteam",
    "defteam",
    "play_type",
    "yardline_100",
}

_ELIGIBLE_PLAY_TYPES = {"run", "pass"}
_SHORT_FIELD_YARDLINE = 60.0
_LONG_FIELD_YARDLINE = 80.0


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


def _drive_starts(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return the first eligible offensive snap of each drive.

    `yardline_100` is distance from the opponent end zone. Lower values
    represent better offensive starting field position.
    """
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    eligible = pbp.filter(
        pl.col("drive").is_not_null()
        & pl.col("posteam").is_not_null()
        & pl.col("defteam").is_not_null()
        & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
        & pl.col("yardline_100").is_not_null()
    )

    return (
        eligible.sort(["game_id", "drive"])
        .group_by(["game_id", "season", "week", "drive"], maintain_order=True)
        .agg(
            pl.col("posteam").first().alias("posteam"),
            pl.col("defteam").first().alias("defteam"),
            pl.col("yardline_100")
            .cast(pl.Float64, strict=False)
            .first()
            .alias("start_yardline_100"),
        )
        .with_columns(
            (
                pl.col("start_yardline_100") <= _SHORT_FIELD_YARDLINE
            ).alias("_short_field"),
            (
                pl.col("start_yardline_100") >= _LONG_FIELD_YARDLINE
            ).alias("_long_field"),
        )
    )


def _weekly_offense(starts: pl.DataFrame) -> pl.DataFrame:
    return (
        starts.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_drives_started"),
            pl.col("start_yardline_100")
            .mean()
            .alias("off_avg_start_yardline_100"),
            pl.col("_short_field")
            .cast(pl.Float64)
            .mean()
            .alias("off_short_field_rate"),
            pl.col("_long_field")
            .cast(pl.Float64)
            .mean()
            .alias("off_long_field_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(starts: pl.DataFrame) -> pl.DataFrame:
    return (
        starts.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_opponent_drives_started"),
            pl.col("start_yardline_100")
            .mean()
            .alias("def_avg_opponent_start_yardline_100"),
            pl.col("_short_field")
            .cast(pl.Float64)
            .mean()
            .alias("def_short_field_allowed_rate"),
            pl.col("_long_field")
            .cast(pl.Float64)
            .mean()
            .alias("def_long_field_forced_rate"),
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
        "off_drives_started",
        "def_opponent_drives_started",
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
            "field_position_history_weeks"
        ),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("field_position_history_weeks").fill_null(0),
            (
                pl.col("field_position_history_weeks").fill_null(0) > 0
            ).alias("field_position_known"),
        )
    )


def build_field_position_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame field-position matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    starts = _drive_starts(pbp)
    weekly = _weekly_offense(starts).join(
        _weekly_defense(starts),
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
                pl.col("away_off_avg_start_yardline_100")
                - pl.col("home_off_avg_start_yardline_100")
            ).alias("off_start_field_position_advantage"),
            (
                pl.col("home_def_avg_opponent_start_yardline_100")
                - pl.col("away_def_avg_opponent_start_yardline_100")
            ).alias("def_field_position_advantage"),
            (
                pl.col("home_off_short_field_rate")
                - pl.col("away_off_short_field_rate")
            ).alias("short_field_rate_difference"),
            (
                pl.col("away_off_long_field_rate")
                - pl.col("home_off_long_field_rate")
            ).alias("long_field_avoidance_advantage"),
            (
                (
                    pl.col("away_off_avg_start_yardline_100")
                    - pl.col("home_off_avg_start_yardline_100")
                )
                + (
                    pl.col("home_def_avg_opponent_start_yardline_100")
                    - pl.col("away_def_avg_opponent_start_yardline_100")
                )
            ).alias("hidden_yards_field_position_advantage"),
        )
    )
