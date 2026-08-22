"""Leakage-safe pregame opponent-adjusted efficiency features."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {"game_id", "season", "week", "home_team", "away_team"}
_REQUIRED_PBP = {
    "game_id", "season", "week", "posteam", "defteam", "play_type", "epa"
}
_ELIGIBLE_PLAY_TYPES = {"run", "pass"}


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _weekly_team_efficiency(pbp: pl.DataFrame) -> pl.DataFrame:
    _require(pbp, _REQUIRED_PBP, "Play-by-play")
    plays = (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
            & pl.col("epa").is_not_null()
        )
        .with_columns(pl.col("epa").cast(pl.Float64, strict=False).alias("_epa"))
        .filter(pl.col("_epa").is_not_null())
    )

    offense = (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_plays"),
            pl.col("_epa").mean().alias("off_epa_per_play"),
        )
        .rename({"posteam": "team"})
    )
    defense = (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_plays_faced"),
            pl.col("_epa").mean().alias("def_epa_allowed_per_play"),
        )
        .rename({"defteam": "team"})
    )
    return offense.join(
        defense,
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )


def _team_schedule(schedule: pl.DataFrame) -> pl.DataFrame:
    return pl.concat(
        [
            schedule.select(
                "game_id", "season", "week",
                pl.col("home_team").alias("team"),
                pl.col("away_team").alias("opponent"),
                pl.lit("home").alias("side"),
            ),
            schedule.select(
                "game_id", "season", "week",
                pl.col("away_team").alias("team"),
                pl.col("home_team").alias("opponent"),
                pl.lit("away").alias("side"),
            ),
        ]
    )


def _pregame_team_baselines(
    targets: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    history = (
        targets.join(
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
    return history.group_by(
        ["game_id", "season", "week", "team", "opponent", "side"]
    ).agg(
        pl.col("off_plays").sum().alias("season_off_plays"),
        pl.col("def_plays_faced").sum().alias("season_def_plays_faced"),
        pl.col("off_epa_per_play").mean().alias("season_off_epa"),
        pl.col("def_epa_allowed_per_play").mean().alias("season_def_epa_allowed"),
        pl.col("week_history").n_unique().alias("opponent_adjusted_history_weeks"),
    )


def _opponent_strength_at_target(
    targets: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    prior = (
        targets.select(
            pl.col("game_id").alias("target_game_id"),
            "season",
            pl.col("week").alias("target_week"),
            "team",
            "side",
        )
        .join(
            targets.select(
                "season",
                pl.col("week").alias("played_week"),
                pl.col("team").alias("played_team"),
                pl.col("opponent").alias("prior_opponent"),
            ),
            left_on=["season", "team"],
            right_on=["season", "played_team"],
            how="left",
        )
        .filter(
            pl.col("played_week").is_not_null()
            & (pl.col("played_week") < pl.col("target_week"))
        )
    )

    opponent_history = (
        prior.join(
            weekly,
            left_on=["season", "prior_opponent"],
            right_on=["season", "team"],
            how="left",
            suffix="_opp_history",
        )
        .filter(
            pl.col("week").is_not_null()
            & (pl.col("week") < pl.col("target_week"))
        )
        .group_by(
            ["target_game_id", "season", "target_week", "side", "prior_opponent"]
        )
        .agg(
            pl.col("off_epa_per_play").mean().alias("_prior_opponent_off_epa"),
            pl.col("def_epa_allowed_per_play")
            .mean()
            .alias("_prior_opponent_def_epa_allowed"),
        )
    )

    return (
        opponent_history.group_by(
            ["target_game_id", "season", "target_week", "side"]
        )
        .agg(
            pl.col("_prior_opponent_off_epa")
            .mean()
            .alias("schedule_opponent_off_epa"),
            pl.col("_prior_opponent_def_epa_allowed")
            .mean()
            .alias("schedule_opponent_def_epa_allowed"),
            pl.col("prior_opponent").n_unique().alias("opponent_adjusted_opponents"),
        )
        .rename({"target_game_id": "game_id", "target_week": "week"})
    )


def _team_features(
    schedule: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    targets = _team_schedule(schedule)
    baselines = _pregame_team_baselines(targets, weekly)
    schedule_strength = _opponent_strength_at_target(targets, weekly)

    return (
        targets.join(
            baselines,
            on=["game_id", "season", "week", "team", "opponent", "side"],
            how="left",
        )
        .join(
            schedule_strength,
            on=["game_id", "season", "week", "side"],
            how="left",
        )
        .with_columns(
            pl.col("opponent_adjusted_history_weeks").fill_null(0),
            pl.col("opponent_adjusted_opponents").fill_null(0),
        )
        .with_columns(
            (
                (pl.col("opponent_adjusted_history_weeks") >= 2)
                & (pl.col("opponent_adjusted_opponents") >= 2)
            ).alias("opponent_adjusted_known"),
            (
                pl.col("season_off_epa")
                - pl.col("schedule_opponent_def_epa_allowed")
            ).alias("opponent_adjusted_off_epa"),
            (
                pl.col("schedule_opponent_off_epa")
                - pl.col("season_def_epa_allowed")
            ).alias("opponent_adjusted_def_epa"),
        )
    )


def build_opponent_adjusted_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")
    weekly = _weekly_team_efficiency(pbp)
    team = _team_features(schedule, weekly)

    metric_columns = [
        column
        for column in team.columns
        if column not in {
            "game_id", "season", "week", "team", "opponent", "side"
        }
    ]

    home = team.filter(pl.col("side") == "home").select(
        "game_id",
        *[pl.col(column).alias(f"home_{column}") for column in metric_columns],
    )
    away = team.filter(pl.col("side") == "away").select(
        "game_id",
        *[pl.col(column).alias(f"away_{column}") for column in metric_columns],
    )

    return (
        schedule.select("game_id", "season", "week", "home_team", "away_team")
        .join(home, on="game_id", how="left")
        .join(away, on="game_id", how="left")
        .with_columns(
            (
                pl.col("home_opponent_adjusted_off_epa")
                - pl.col("away_opponent_adjusted_off_epa")
            ).alias("opponent_adjusted_off_epa_difference"),
            (
                pl.col("home_opponent_adjusted_def_epa")
                - pl.col("away_opponent_adjusted_def_epa")
            ).alias("opponent_adjusted_def_epa_difference"),
            (
                pl.col("away_schedule_opponent_def_epa_allowed")
                - pl.col("home_schedule_opponent_def_epa_allowed")
            ).alias("offensive_schedule_difficulty_advantage"),
            (
                pl.col("home_schedule_opponent_off_epa")
                - pl.col("away_schedule_opponent_off_epa")
            ).alias("defensive_schedule_difficulty_advantage"),
        )
    )
