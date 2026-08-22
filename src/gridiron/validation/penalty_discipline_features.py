"""Validation for penalty-discipline feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_penalty_discipline_known",
    "away_penalty_discipline_known",
    "home_discipline_history_weeks",
    "away_discipline_history_weeks",
    "penalty_yards_discipline_advantage",
    "penalty_rate_discipline_advantage",
    "offensive_penalty_discipline_advantage",
    "defensive_penalty_discipline_advantage",
}


def validate_penalty_discipline_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Penalty-discipline features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Penalty-discipline features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Penalty-discipline features contain invalid week values."
        )
