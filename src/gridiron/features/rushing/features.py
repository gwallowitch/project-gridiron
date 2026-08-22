"""Leakage-safe pregame rushing-efficiency features."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {"game_id", "season", "week", "home_team", "away_team"}
_REQUIRED_PBP = {
    "game_id", "season", "week", "posteam", "defteam",
    "rush_attempt", "yards_gained", "epa", "success",
}


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _rushing_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return qualifying rushing plays, excluding kneels when identifiable."""
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    qualifying = pl.col("rush_attempt").fill_null(0) == 1
    if "qb_kneel" in pbp.columns:
        qualifying = qualifying & (pl.col("qb_kneel").fill_null(0) == 0)

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
            .fill_null(0.0)
            .alias("_rush_success"),
            (
                pl.col("yards_gained")
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
                >= 10.0
            )
            .cast(pl.Float64)
            .alias("_explosive_run"),
        )
    )


def _weekly_offense(rushing: pl.DataFrame) -> pl.DataFrame:
    return (
        rushing.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_rush_plays"),
            pl.col("epa").mean().alias("off_rush_epa_per_play"),
            pl.col("_rush_success").mean().alias("off_rush_success_rate"),
            pl.col("_explosive_run").mean().alias("off_explosive_run_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(rushing: pl.DataFrame) -> pl.DataFrame:
    return (
        rushing.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_rush_plays"),
            pl.col("epa").mean().alias("def_rush_epa_allowed_per_play"),
            pl.col("_rush_success").mean().alias("def_rush_success_rate_allowed"),
            pl.col("_explosive_run").mean().alias("def_explosive_run_rate_allowed"),
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
                if c.endswith("_plays")
                else pl.col(c).mean()
            ).alias(c)
            for c in metric_columns
        ],
        pl.col("week_history").n_unique().alias("rushing_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("rushing_history_weeks").fill_null(0),
            (pl.col("rushing_history_weeks").fill_null(0) > 0)
            .alias("rushing_known"),
        )
    )


def build_rushing_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build game-level pregame rushing features using only prior weeks."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    rushing = _rushing_plays(pbp)
    offense = _weekly_offense(rushing)
    defense = _weekly_defense(rushing)
    weekly = offense.join(
        defense,
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
                pl.col("home_off_rush_epa_per_play")
                - pl.col("away_off_rush_epa_per_play")
            ).alias("rush_off_epa_difference"),
            (
                pl.col("away_def_rush_epa_allowed_per_play")
                - pl.col("home_def_rush_epa_allowed_per_play")
            ).alias("rush_def_epa_difference"),
            (
                pl.col("home_off_rush_success_rate")
                - pl.col("away_off_rush_success_rate")
            ).alias("rush_success_difference"),
            (
                pl.col("home_off_explosive_run_rate")
                - pl.col("away_off_explosive_run_rate")
            ).alias("explosive_run_rate_difference"),
        )
    )
