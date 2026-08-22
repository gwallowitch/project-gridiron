"""Validation for rushing feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id", "season", "week", "home_team", "away_team",
    "home_rushing_known", "away_rushing_known",
    "home_rushing_history_weeks", "away_rushing_history_weeks",
    "rush_off_epa_difference", "rush_def_epa_difference",
    "rush_success_difference", "explosive_run_rate_difference",
}


def validate_rushing_features(frame: pl.DataFrame) -> None:
    """Raise when a rushing feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Rushing features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Rushing features contain duplicate game_id values.")

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("Rushing features contain invalid week values.")
