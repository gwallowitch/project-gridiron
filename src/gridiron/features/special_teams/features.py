"""Leakage-safe pregame special-teams features."""

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
    "field_goal_result",
    "kick_distance",
    "punt_attempt",
    "punter_player_name",
    "return_yards",
    "touchback",
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


def _field_goal_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    return (
        pbp.filter(
            (pl.col("play_type") == "field_goal")
            & pl.col("posteam").is_not_null()
            & pl.col("kick_distance").is_not_null()
            & pl.col("field_goal_result").is_not_null()
        )
        .with_columns(
            (pl.col("field_goal_result") == "made")
            .cast(pl.Float64)
            .alias("_fg_made"),
            (pl.col("kick_distance") >= 50)
            .cast(pl.Float64)
            .alias("_fg_50_plus"),
        )
    )


def _punt_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    return (
        pbp.filter(
            (pl.col("punt_attempt").fill_null(0) == 1)
            & pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
        )
        .with_columns(
            pl.col("return_yards")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_punt_return_yards"),
            pl.col("touchback")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_punt_touchback"),
        )
    )


def _weekly_field_goal_offense(fg: pl.DataFrame) -> pl.DataFrame:
    return (
        fg.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("fg_attempts"),
            pl.col("_fg_made").mean().alias("fg_make_rate"),
            pl.col("kick_distance").mean().alias("avg_fg_distance"),
            pl.col("_fg_50_plus").mean().alias("fg_50_plus_attempt_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_punting_offense(punts: pl.DataFrame) -> pl.DataFrame:
    return (
        punts.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("punt_attempts"),
            pl.col("_punt_return_yards")
            .mean()
            .alias("punt_return_yards_allowed"),
            pl.col("_punt_touchback").mean().alias("punt_touchback_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_punt_return_defense(punts: pl.DataFrame) -> pl.DataFrame:
    return (
        punts.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("punt_returns_faced"),
            pl.col("_punt_return_yards")
            .mean()
            .alias("punt_return_yards_gained"),
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
        c for c in weekly.columns if c not in {"season", "week", "team"}
    ]

    rolled = history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        *[
            (
                pl.col(c).sum()
                if c.endswith(("_attempts", "_faced"))
                else pl.col(c).mean()
            ).alias(c)
            for c in metric_columns
        ],
        pl.col("week_history").n_unique().alias("special_teams_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("special_teams_history_weeks").fill_null(0),
            (
                pl.col("special_teams_history_weeks").fill_null(0) > 0
            ).alias("special_teams_known"),
        )
    )


def build_special_teams_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame special-teams features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    fg = _weekly_field_goal_offense(_field_goal_plays(pbp))
    punt = _weekly_punting_offense(_punt_plays(pbp))
    ret = _weekly_punt_return_defense(_punt_plays(pbp))

    weekly = fg.join(
        punt,
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    ).join(
        ret,
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
                pl.col("home_fg_make_rate")
                - pl.col("away_fg_make_rate")
            ).alias("fg_make_rate_difference"),
            (
                pl.col("away_punt_return_yards_allowed")
                - pl.col("home_punt_return_yards_allowed")
            ).alias("punt_coverage_advantage"),
            (
                pl.col("home_punt_return_yards_gained")
                - pl.col("away_punt_return_yards_gained")
            ).alias("punt_return_advantage"),
            (
                pl.col("away_punt_touchback_rate")
                - pl.col("home_punt_touchback_rate")
            ).alias("punt_touchback_advantage"),
        )
    )
