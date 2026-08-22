"""Leakage-safe pregame neutral game-state efficiency features."""

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
    "epa",
    "yards_gained",
    "score_differential",
    "game_seconds_remaining",
}

_ELIGIBLE_PLAY_TYPES = {"run", "pass"}
_MAX_NEUTRAL_SCORE_MARGIN = 8.0
_MIN_GAME_SECONDS_REMAINING = 300.0
_EXPLOSIVE_YARDS = 15.0


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


def _neutral_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    """Return scrimmage plays played in a relatively neutral game state.

    Neutral-state policy:
    - run/pass scrimmage plays only;
    - offense/defense are known;
    - absolute pre-snap score differential is <= 8 points;
    - at least 5:00 remains in regulation.

    The final five minutes are excluded because clock/score incentives become
    increasingly non-stationary even in one-score games.
    """
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    return (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("play_type").is_in(list(_ELIGIBLE_PLAY_TYPES))
            & pl.col("score_differential").is_not_null()
            & pl.col("game_seconds_remaining").is_not_null()
            & (
                pl.col("score_differential")
                .cast(pl.Float64, strict=False)
                .abs()
                <= _MAX_NEUTRAL_SCORE_MARGIN
            )
            & (
                pl.col("game_seconds_remaining")
                .cast(pl.Float64, strict=False)
                >= _MIN_GAME_SECONDS_REMAINING
            )
        )
        .with_columns(
            pl.col("epa")
            .cast(pl.Float64, strict=False)
            .gt(0.0)
            .alias("_success"),
            pl.col("yards_gained")
            .cast(pl.Float64, strict=False)
            .ge(_EXPLOSIVE_YARDS)
            .alias("_explosive"),
        )
    )


def _weekly_offense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "posteam"])
        .agg(
            pl.len().alias("off_neutral_plays"),
            pl.col("epa")
            .cast(pl.Float64, strict=False)
            .drop_nulls()
            .mean()
            .alias("off_neutral_epa"),
            pl.col("_success")
            .cast(pl.Float64)
            .mean()
            .alias("off_neutral_success_rate"),
            pl.col("yards_gained")
            .cast(pl.Float64, strict=False)
            .drop_nulls()
            .mean()
            .alias("off_neutral_yards_per_play"),
            pl.col("_explosive")
            .cast(pl.Float64)
            .mean()
            .alias("off_neutral_explosive_rate"),
        )
        .rename({"posteam": "team"})
    )


def _weekly_defense(plays: pl.DataFrame) -> pl.DataFrame:
    return (
        plays.group_by(["season", "week", "defteam"])
        .agg(
            pl.len().alias("def_neutral_plays"),
            pl.col("epa")
            .cast(pl.Float64, strict=False)
            .drop_nulls()
            .mean()
            .alias("def_neutral_epa_allowed"),
            pl.col("_success")
            .cast(pl.Float64)
            .mean()
            .alias("def_neutral_success_rate_allowed"),
            pl.col("yards_gained")
            .cast(pl.Float64, strict=False)
            .drop_nulls()
            .mean()
            .alias("def_neutral_yards_per_play_allowed"),
            pl.col("_explosive")
            .cast(pl.Float64)
            .mean()
            .alias("def_neutral_explosive_rate_allowed"),
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
    """Use only same-season observations from weeks before the target game."""
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
        "off_neutral_plays",
        "def_neutral_plays",
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
        pl.col("week_history").n_unique().alias("neutral_state_history_weeks"),
    )

    return (
        schedule_teams.join(
            rolled,
            on=["game_id", "season", "week", "team", "side"],
            how="left",
        )
        .with_columns(
            pl.col("neutral_state_history_weeks").fill_null(0),
            (
                pl.col("neutral_state_history_weeks").fill_null(0) > 0
            ).alias("neutral_state_known"),
        )
    )


def build_neutral_state_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
) -> pl.DataFrame:
    """Build leakage-safe pregame neutral-state matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    plays = _neutral_plays(pbp)
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
                pl.col("home_off_neutral_epa")
                - pl.col("away_off_neutral_epa")
            ).alias("neutral_off_epa_difference"),
            (
                pl.col("away_def_neutral_epa_allowed")
                - pl.col("home_def_neutral_epa_allowed")
            ).alias("neutral_def_epa_difference"),
            (
                pl.col("home_off_neutral_success_rate")
                - pl.col("away_off_neutral_success_rate")
            ).alias("neutral_success_difference"),
            (
                pl.col("home_off_neutral_yards_per_play")
                - pl.col("away_off_neutral_yards_per_play")
            ).alias("neutral_yards_per_play_difference"),
            (
                pl.col("home_off_neutral_explosive_rate")
                - pl.col("away_off_neutral_explosive_rate")
            ).alias("neutral_explosive_rate_difference"),
        )
    )
