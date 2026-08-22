"""Validation for pressure/pass-protection feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_pressure_known",
    "away_pressure_known",
    "home_pressure_history_weeks",
    "away_pressure_history_weeks",
    "pass_protection_advantage",
    "pressure_creation_advantage",
    "clean_dropback_advantage",
    "pressured_off_epa_difference",
    "pressured_def_epa_advantage",
}


def validate_pressure_features(frame: pl.DataFrame) -> None:
    """Raise when a pressure feature artifact is structurally invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Pressure features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Pressure features contain duplicate game_id values.")

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("Pressure features contain invalid week values.")
