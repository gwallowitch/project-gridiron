"""Build category and overall team ratings."""

from __future__ import annotations

import polars as pl

from gridiron.ratings.normalization import normalize_metrics
from gridiron.ratings.weights import (
    DEFENSE_WEIGHT,
    DISCIPLINE_WEIGHT,
    OFFENSE_WEIGHT,
    SITUATIONAL_WEIGHT,
    TOTAL_WEIGHT,
)

OFFENSIVE_METRICS = {
    "offensive_epa_per_play": True,
    "offensive_success_rate": True,
    "offensive_yards_per_play": True,
    "explosive_play_rate": True,
}

DEFENSIVE_METRICS = {
    "defensive_epa_allowed_per_play": False,
    "defensive_success_rate_allowed": False,
    "defensive_explosive_play_rate_allowed": False,
}

DISCIPLINE_METRICS = {
    "turnover_margin": True,
}

REQUIRED_COLUMNS = frozenset(
    {
        "team",
        *OFFENSIVE_METRICS,
        *DEFENSIVE_METRICS,
        *DISCIPLINE_METRICS,
    }
)


def build_team_ratings(team_metrics: pl.DataFrame) -> pl.DataFrame:
    """Build offense, defense, discipline, and overall ratings."""
    _validate_inputs(team_metrics)
    _validate_weights()

    normalized = normalize_metrics(
        team_metrics,
        {
            **OFFENSIVE_METRICS,
            **DEFENSIVE_METRICS,
            **DISCIPLINE_METRICS,
        },
    )

    rated = normalized.with_columns(
        pl.mean_horizontal(
            [
                "offensive_epa_per_play_rating",
                "offensive_success_rate_rating",
                "offensive_yards_per_play_rating",
                "explosive_play_rate_rating",
            ]
        ).alias("offense_rating"),
        pl.mean_horizontal(
            [
                "defensive_epa_allowed_per_play_rating",
                "defensive_success_rate_allowed_rating",
                "defensive_explosive_play_rate_allowed_rating",
            ]
        ).alias("defense_rating"),
        pl.col("turnover_margin_rating").alias("discipline_rating"),
        pl.lit(100.0).alias("situational_rating"),
    ).with_columns(
        (
            pl.col("offense_rating") * OFFENSE_WEIGHT
            + pl.col("defense_rating") * DEFENSE_WEIGHT
            + pl.col("discipline_rating") * DISCIPLINE_WEIGHT
            + pl.col("situational_rating") * SITUATIONAL_WEIGHT
        ).alias("overall_rating")
    )

    return rated.select(
        "team",
        "games_played",
        "offense_rating",
        "defense_rating",
        "discipline_rating",
        "situational_rating",
        "overall_rating",
    ).sort(
        "overall_rating",
        descending=True,
    )


def _validate_inputs(frame: pl.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(frame.columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Team metrics are missing required columns: {missing_text}"
        )

    if frame.height < 2:
        raise ValueError(
            "Team ratings require metrics for at least two teams."
        )

    if frame["team"].n_unique() != frame.height:
        raise ValueError(
            "Team metrics must contain exactly one row per team."
        )


def _validate_weights() -> None:
    if abs(TOTAL_WEIGHT - 1.0) > 1e-9:
        raise ValueError(
            f"Rating category weights must total 1.0; got {TOTAL_WEIGHT}."
        )