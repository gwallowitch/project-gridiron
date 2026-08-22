"""Validation for neutral game-state feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_neutral_state_known",
    "away_neutral_state_known",
    "home_neutral_state_history_weeks",
    "away_neutral_state_history_weeks",
    "neutral_off_epa_difference",
    "neutral_def_epa_difference",
    "neutral_success_difference",
    "neutral_yards_per_play_difference",
    "neutral_explosive_rate_difference",
}


def validate_neutral_state_features(frame: pl.DataFrame) -> None:
    """Raise when a neutral-state feature artifact is structurally invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Neutral-state features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Neutral-state features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Neutral-state features contain invalid week values."
        )
