"""Validation for opponent-adjusted feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_opponent_adjusted_known",
    "away_opponent_adjusted_known",
    "home_opponent_adjusted_history_weeks",
    "away_opponent_adjusted_history_weeks",
    "home_opponent_adjusted_opponents",
    "away_opponent_adjusted_opponents",
    "opponent_adjusted_off_epa_difference",
    "opponent_adjusted_def_epa_difference",
    "offensive_schedule_difficulty_advantage",
    "defensive_schedule_difficulty_advantage",
}


def validate_opponent_adjusted_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Opponent-adjusted features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Opponent-adjusted features contain duplicate game_id values."
        )
    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Opponent-adjusted features contain invalid week values."
        )
