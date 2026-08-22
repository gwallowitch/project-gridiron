"""Leakage-safe pregame passing-efficiency features."""

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
    "pass_attempt",
    "sack",
    "epa",
    "success",
    "yards_gained",
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


def _dropbacks(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return qualifying dropbacks with stable derived indicators."""
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    if "qb_dropback" in pbp.columns:
        qualifying = pl.col("qb_dropback").fill_null(0) == 1
    else:
        qualifying = (
            (pl.col("pass_attempt").fill_null(0) == 1)
            | (pl.col("sack").fill_null(0) == 1)
        )

    return (
        pbp.filter(
            qualifying
            & pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("epa").is_not_null()
        )
        .with_columns(
            pl.col("success")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0),
            pl.col("sack")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("_sack"),
            (
                (pl.col("pass_attempt").fill_null(0) == 1)
                & (pl.col("yards_gained").fill_null(0.0) >= 20.0)
            )
            .cast(pl.Float64)
            .alias("_explosive_pass"),
        )
    )


def _team_week_offense(
    dropbacks: pl.DataFrame,
) -> pl.DataFrame:
    return (
        dropbacks.group_by(
            ["season", "week", "posteam"]
        )
        .agg(
            pl.len().alias("off_dropbacks"),
            pl.col("epa")
            .mean()
            .alias("off_pass_epa_per_dropback"),
            pl.col("success")
            .mean()
            .alias("off_pass_success_rate"),
            pl.col("_sack")
            .mean()
            .alias("off_sack_rate"),
            pl.col("_explosive_pass")
            .mean()
            .alias("off_explosive_pass_rate"),
        )
        .rename({"posteam": "team"})
    )


def _team_week_defense(
    dropbacks: pl.DataFrame,
) -> pl.DataFrame:
    return (
        dropbacks.group_by(
            ["season", "week", "defteam"]
        )
        .agg(
            pl.len().alias("def_dropbacks"),
            pl.col("epa")
            .mean()
            .alias("def_pass_epa_allowed_per_dropback"),
            pl.col("success")
            .mean()
            .alias("def_pass_success_rate_allowed"),
            pl.col("_sack")
            .mean()
            .alias("def_sack_rate_generated"),
            pl.col("_explosive_pass")
            .mean()
            .alias("def_explosive_pass_rate_allowed"),
        )
        .rename({"defteam": "team"})
    )


def _schedule_teams(
    schedule: pl.DataFrame,
) -> pl.DataFrame:
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
    """Roll only strictly earlier weeks into the current game."""
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
    aggregations: list[pl.Expr] = []
    for column in metric_columns:
        if column.endswith("dropbacks"):
            aggregations.append(
                pl.col(column).sum().alias(column)
            )
        else:
            aggregations.append(
                pl.col(column).mean().alias(column)
            )

    rolled = history.group_by(
        [
            "game_id",
            "season",
            "week",
            "team",
            "side",
        ]
    ).agg(
        *aggregations,
        pl.col("week_history")
        .n_unique()
        .alias("passing_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=[
                "game_id",
                "season",
                "week",
                "team",
                "side",
            ],
            how="left",
        )
        .with_columns(
            pl.col("passing_history_weeks").fill_null(0),
            (
                pl.col("passing_history_weeks").fill_null(0)
                > 0
            ).alias("passing_known"),
        )
    )


def build_passing_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build game-level pregame passing-efficiency features.

    For a game in week N, only play-by-play from weeks strictly less
    than N in the same season may contribute.
    """
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    dropbacks = _dropbacks(pbp)
    offense = _team_week_offense(dropbacks)
    defense = _team_week_defense(dropbacks)
    weekly = offense.join(
        defense,
        on=["season", "week", "team"],
        how="full",
        coalesce=True,
    )

    schedule_teams = _schedule_teams(schedule)
    team = _pregame_team_features(
        schedule_teams,
        weekly,
    )

    metric_columns = [
        column
        for column in team.columns
        if column
        not in {
            "game_id",
            "season",
            "week",
            "team",
            "side",
        }
    ]

    home = (
        team.filter(pl.col("side") == "home")
        .select(
            "game_id",
            *[
                pl.col(column).alias(
                    f"home_{column}"
                )
                for column in metric_columns
            ],
        )
    )
    away = (
        team.filter(pl.col("side") == "away")
        .select(
            "game_id",
            *[
                pl.col(column).alias(
                    f"away_{column}"
                )
                for column in metric_columns
            ],
        )
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
                pl.col("home_off_pass_epa_per_dropback")
                - pl.col("away_off_pass_epa_per_dropback")
            ).alias("pass_off_epa_difference"),
            (
                pl.col(
                    "away_def_pass_epa_allowed_per_dropback"
                )
                - pl.col(
                    "home_def_pass_epa_allowed_per_dropback"
                )
            ).alias("pass_def_epa_difference"),
            (
                pl.col("home_off_pass_success_rate")
                - pl.col("away_off_pass_success_rate")
            ).alias("pass_success_difference"),
            (
                pl.col("away_off_sack_rate")
                - pl.col("home_off_sack_rate")
            ).alias("off_sack_rate_advantage"),
            (
                pl.col("home_def_sack_rate_generated")
                - pl.col("away_def_sack_rate_generated")
            ).alias("def_sack_rate_advantage"),
            (
                pl.col("home_off_explosive_pass_rate")
                - pl.col("away_off_explosive_pass_rate")
            ).alias("explosive_pass_rate_difference"),
        )
    )
