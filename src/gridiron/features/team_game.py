"""Team-level game features derived from nflverse play-by-play data."""

from __future__ import annotations

import polars as pl

from gridiron.validation.play_by_play import validate_play_by_play

_REQUIRED_FEATURE_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "posteam",
        "defteam",
        "play_type",
        "epa",
        "success",
        "yards_gained",
        "pass_attempt",
        "rush_attempt",
        "interception",
        "fumble_lost",
    }
)


def build_team_game_features(play_by_play: pl.DataFrame) -> pl.DataFrame:
    """Create one feature row per offensive team per game."""
    validate_play_by_play(play_by_play)
    _validate_feature_columns(play_by_play)

    offensive_plays = play_by_play.filter(
        pl.col("play_type").is_in(["pass", "run"])
        & pl.col("posteam").is_not_null()
        & pl.col("defteam").is_not_null()
        & pl.col("epa").is_not_null()
    ).with_columns(
        (
            (pl.col("play_type") == "pass")
            & (pl.col("yards_gained") >= 20)
            | (pl.col("play_type") == "run")
            & (pl.col("yards_gained") >= 10)
        )
        .cast(pl.Int8)
        .alias("explosive_play"),
        (
            pl.col("interception").fill_null(0)
            + pl.col("fumble_lost").fill_null(0)
        )
        .gt(0)
        .cast(pl.Int8)
        .alias("turnover"),
    )

    offense = (
        offensive_plays.group_by(
            ["game_id", "season", "week", "posteam", "defteam"]
        )
        .agg(
            pl.len().alias("offensive_plays"),
            pl.col("yards_gained").sum().alias("offensive_yards"),
            pl.col("epa").sum().alias("offensive_epa"),
            pl.col("epa").mean().alias("offensive_epa_per_play"),
            pl.col("success").mean().alias("offensive_success_rate"),
            pl.col("explosive_play").mean().alias("explosive_play_rate"),
            pl.col("turnover").sum().alias("turnovers"),
            pl.col("turnover").mean().alias("turnover_rate"),
            pl.col("pass_attempt").fill_null(0).sum().alias("pass_attempts"),
            pl.col("rush_attempt").fill_null(0).sum().alias("rush_attempts"),
            pl.when(pl.col("play_type") == "pass")
            .then(pl.col("epa"))
            .otherwise(None)
            .mean()
            .alias("passing_epa_per_play"),
            pl.when(pl.col("play_type") == "run")
            .then(pl.col("epa"))
            .otherwise(None)
            .mean()
            .alias("rushing_epa_per_play"),
        )
        .rename(
            {
                "posteam": "team",
                "defteam": "opponent",
            }
        )
    )

    defense = offense.select(
        "game_id",
        pl.col("team").alias("opponent"),
        pl.col("opponent").alias("team"),
        pl.col("offensive_epa_per_play").alias(
            "defensive_epa_allowed_per_play"
        ),
        pl.col("offensive_success_rate").alias(
            "defensive_success_rate_allowed"
        ),
        pl.col("explosive_play_rate").alias(
            "defensive_explosive_play_rate_allowed"
        ),
        pl.col("turnovers").alias("takeaways"),
    )

    return (
        offense.join(
            defense,
            on=["game_id", "team", "opponent"],
            how="left",
            validate="1:1",
        )
        .select(
            "game_id",
            "season",
            "week",
            "team",
            "opponent",
            "offensive_plays",
            "offensive_yards",
            "offensive_epa",
            "offensive_epa_per_play",
            "offensive_success_rate",
            "passing_epa_per_play",
            "rushing_epa_per_play",
            "explosive_play_rate",
            "turnovers",
            "turnover_rate",
            "pass_attempts",
            "rush_attempts",
            "defensive_epa_allowed_per_play",
            "defensive_success_rate_allowed",
            "defensive_explosive_play_rate_allowed",
            "takeaways",
        )
        .sort(["season", "week", "game_id", "team"])
    )


def _validate_feature_columns(frame: pl.DataFrame) -> None:
    missing = _REQUIRED_FEATURE_COLUMNS.difference(frame.columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Feature input is missing columns: {missing_text}"
        )
