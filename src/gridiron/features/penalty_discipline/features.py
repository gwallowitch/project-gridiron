"""Leakage-safe pregame penalty-discipline features."""

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
    "penalty_team",
    "penalty_yards",
}

_ELIGIBLE_PLAY_TYPES = {
    "run",
    "pass",
    "punt",
    "field_goal",
    "kickoff",
    "extra_point",
    "no_play",
}


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _weekly_team_discipline(pbp: pl.DataFrame) -> pl.DataFrame:
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    plays = (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
        )
        .with_columns(
            pl.col("penalty_yards")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_penalty_yards"),
            pl.col("penalty_team").is_not_null().alias("_has_penalty"),
        )
    )

    offense = (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_plays"),
            (
                (pl.col("penalty_team") == pl.col("posteam"))
                .cast(pl.Int64)
                .sum()
            ).alias("off_penalties"),
            (
                pl.when(pl.col("penalty_team") == pl.col("posteam"))
                .then(pl.col("_penalty_yards"))
                .otherwise(0.0)
                .sum()
            ).alias("off_penalty_yards"),
        )
        .rename({"posteam": "team"})
    )

    defense = (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_plays"),
            (
                (pl.col("penalty_team") == pl.col("defteam"))
                .cast(pl.Int64)
                .sum()
            ).alias("def_penalties"),
            (
                pl.when(pl.col("penalty_team") == pl.col("defteam"))
                .then(pl.col("_penalty_yards"))
                .otherwise(0.0)
                .sum()
            ).alias("def_penalty_yards"),
        )
        .rename({"defteam": "team"})
    )

    return (
        offense.join(
            defense,
            on=["season", "week", "team"],
            how="full",
            coalesce=True,
        )
        .with_columns(
            (
                100.0 * pl.col("off_penalties") / pl.col("off_plays")
            ).alias("off_penalties_per_100"),
            (
                100.0 * pl.col("off_penalty_yards") / pl.col("off_plays")
            ).alias("off_penalty_yards_per_100"),
            (
                100.0 * pl.col("def_penalties") / pl.col("def_plays")
            ).alias("def_penalties_per_100"),
            (
                100.0 * pl.col("def_penalty_yards") / pl.col("def_plays")
            ).alias("def_penalty_yards_per_100"),
        )
    )


def _team_schedule(schedule: pl.DataFrame) -> pl.DataFrame:
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
    schedule: pl.DataFrame,
    weekly: pl.DataFrame,
) -> pl.DataFrame:
    targets = _team_schedule(schedule)

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

    rolled = history.group_by(
        ["game_id", "season", "week", "team", "side"]
    ).agg(
        pl.col("off_plays").sum().alias("discipline_off_plays"),
        pl.col("def_plays").sum().alias("discipline_def_plays"),
        pl.col("off_penalties").sum().alias("off_penalties"),
        pl.col("off_penalty_yards").sum().alias("off_penalty_yards"),
        pl.col("def_penalties").sum().alias("def_penalties"),
        pl.col("def_penalty_yards").sum().alias("def_penalty_yards"),
        pl.col("week_history").n_unique().alias("discipline_history_weeks"),
    )

    return (
        targets.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("discipline_history_weeks").fill_null(0),
            (
                pl.col("discipline_history_weeks").fill_null(0) >= 2
            ).alias("penalty_discipline_known"),
        )
        .with_columns(
            (
                100.0 * pl.col("off_penalties") / pl.col("discipline_off_plays")
            ).alias("off_penalties_per_100"),
            (
                100.0
                * pl.col("off_penalty_yards")
                / pl.col("discipline_off_plays")
            ).alias("off_penalty_yards_per_100"),
            (
                100.0 * pl.col("def_penalties") / pl.col("discipline_def_plays")
            ).alias("def_penalties_per_100"),
            (
                100.0
                * pl.col("def_penalty_yards")
                / pl.col("discipline_def_plays")
            ).alias("def_penalty_yards_per_100"),
        )
        .with_columns(
            (
                pl.col("off_penalty_yards_per_100")
                + pl.col("def_penalty_yards_per_100")
            ).alias("total_penalty_yards_per_100"),
            (
                pl.col("off_penalties_per_100")
                + pl.col("def_penalties_per_100")
            ).alias("total_penalties_per_100"),
        )
    )


def build_penalty_discipline_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame penalty-discipline matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    weekly = _weekly_team_discipline(pbp)
    team = _pregame_team_features(schedule, weekly)

    metric_columns = [
        column
        for column in team.columns
        if column not in {
            "game_id",
            "season",
            "week",
            "team",
            "side",
        }
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
                pl.col("away_total_penalty_yards_per_100")
                - pl.col("home_total_penalty_yards_per_100")
            ).alias("penalty_yards_discipline_advantage"),
            (
                pl.col("away_total_penalties_per_100")
                - pl.col("home_total_penalties_per_100")
            ).alias("penalty_rate_discipline_advantage"),
            (
                pl.col("away_off_penalty_yards_per_100")
                - pl.col("home_off_penalty_yards_per_100")
            ).alias("offensive_penalty_discipline_advantage"),
            (
                pl.col("away_def_penalty_yards_per_100")
                - pl.col("home_def_penalty_yards_per_100")
            ).alias("defensive_penalty_discipline_advantage"),
        )
    )
