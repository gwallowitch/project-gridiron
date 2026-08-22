"""Leakage-safe pregame turnover-stability features."""

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
    "interception",
    "fumble",
    "fumble_lost",
}

_ELIGIBLE_PLAY_TYPES = {"run", "pass", "qb_kneel", "qb_spike"}


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


def _turnover_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    return (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
        )
        .with_columns(
            pl.col("interception")
            .cast(pl.Int64, strict=False)
            .fill_null(0)
            .alias("_interception"),
            pl.col("fumble")
            .cast(pl.Int64, strict=False)
            .fill_null(0)
            .alias("_fumble"),
            pl.col("fumble_lost")
            .cast(pl.Int64, strict=False)
            .fill_null(0)
            .alias("_fumble_lost"),
        )
        .with_columns(
            (
                pl.col("_interception") + pl.col("_fumble_lost")
            ).alias("_turnover"),
            (
                pl.col("_fumble") - pl.col("_fumble_lost")
            ).clip(lower_bound=0).alias("_fumble_recovered_by_offense"),
        )
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_turnover_eligible_plays"),
            pl.col("_interception").sum().alias("off_interceptions_thrown"),
            pl.col("_fumble").sum().alias("off_fumbles"),
            pl.col("_fumble_lost").sum().alias("off_fumbles_lost"),
            pl.col("_turnover").sum().alias("off_turnovers"),
            pl.col("_fumble_recovered_by_offense")
            .sum()
            .alias("off_fumbles_recovered"),
        )
        .with_columns(
            (
                pl.col("off_turnovers")
                / pl.col("off_turnover_eligible_plays")
            ).alias("off_turnover_rate"),
            (
                pl.col("off_interceptions_thrown")
                / pl.col("off_turnover_eligible_plays")
            ).alias("off_interception_rate"),
            pl.when(pl.col("off_fumbles") > 0)
            .then(
                pl.col("off_fumbles_lost")
                / pl.col("off_fumbles")
            )
            .otherwise(None)
            .alias("off_fumble_loss_rate"),
            pl.when(pl.col("off_fumbles") > 0)
            .then(
                pl.col("off_fumbles_recovered")
                / pl.col("off_fumbles")
            )
            .otherwise(None)
            .alias("off_fumble_recovery_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_turnover_eligible_plays_faced"),
            pl.col("_interception").sum().alias("def_interceptions_forced"),
            pl.col("_fumble").sum().alias("def_opponent_fumbles"),
            pl.col("_fumble_lost").sum().alias("def_fumbles_recovered"),
            pl.col("_turnover").sum().alias("def_takeaways"),
        )
        .with_columns(
            (
                pl.col("def_takeaways")
                / pl.col("def_turnover_eligible_plays_faced")
            ).alias("def_takeaway_rate"),
            (
                pl.col("def_interceptions_forced")
                / pl.col("def_turnover_eligible_plays_faced")
            ).alias("def_interception_rate"),
            pl.when(pl.col("def_opponent_fumbles") > 0)
            .then(
                pl.col("def_fumbles_recovered")
                / pl.col("def_opponent_fumbles")
            )
            .otherwise(None)
            .alias("def_fumble_recovery_rate"),
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
    """Aggregate only same-season weeks strictly before the target game."""
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
        "off_turnover_eligible_plays",
        "off_interceptions_thrown",
        "off_fumbles",
        "off_fumbles_lost",
        "off_turnovers",
        "off_fumbles_recovered",
        "def_turnover_eligible_plays_faced",
        "def_interceptions_forced",
        "def_opponent_fumbles",
        "def_fumbles_recovered",
        "def_takeaways",
    }
    metric_columns = [
        c
        for c in weekly.columns
        if c not in {"season", "week", "team"}
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
            "turnover_stability_history_weeks"
        ),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("turnover_stability_history_weeks").fill_null(0),
            (
                pl.col("turnover_stability_history_weeks")
                .fill_null(0) > 0
            ).alias("turnover_stability_known"),
        )
    )


def build_turnover_stability_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame turnover-stability matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    plays = _turnover_plays(pbp)
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
                pl.col("away_off_turnover_rate")
                - pl.col("home_off_turnover_rate")
            ).alias("turnover_protection_advantage"),
            (
                pl.col("home_def_takeaway_rate")
                - pl.col("away_def_takeaway_rate")
            ).alias("takeaway_creation_advantage"),
            (
                pl.col("away_off_interception_rate")
                - pl.col("home_off_interception_rate")
            ).alias("interception_protection_advantage"),
            (
                pl.col("home_def_interception_rate")
                - pl.col("away_def_interception_rate")
            ).alias("interception_creation_advantage"),
            (
                pl.col("away_off_fumble_loss_rate")
                - pl.col("home_off_fumble_loss_rate")
            ).alias("off_fumble_luck_advantage"),
            (
                pl.col("home_def_fumble_recovery_rate")
                - pl.col("away_def_fumble_recovery_rate")
            ).alias("def_fumble_luck_advantage"),
            (
                (
                    pl.col("home_off_fumble_recovery_rate")
                    - pl.col("away_off_fumble_recovery_rate")
                )
                + (
                    pl.col("home_def_fumble_recovery_rate")
                    - pl.col("away_def_fumble_recovery_rate")
                )
            ).alias("combined_fumble_recovery_luck"),
        )
    )
