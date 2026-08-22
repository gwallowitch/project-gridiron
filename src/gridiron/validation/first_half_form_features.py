"""Validation for Step 85A first-half form features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_first_half_off_epa",
    "away_first_half_off_epa",
    "home_first_half_def_epa",
    "away_first_half_def_epa",
    "home_first_half_play_volume",
    "away_first_half_play_volume",
    "home_first_half_form_known",
    "away_first_half_form_known",
    "first_half_off_epa_advantage",
    "first_half_def_epa_advantage",
    "first_half_play_volume_advantage",
}


def validate_first_half_form_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "First-half form features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "First-half form features contain duplicate game_id rows."
        )

    for column in (
        "home_first_half_play_volume",
        "away_first_half_play_volume",
    ):
        if frame.filter(
            pl.col(column).is_not_null()
            & (pl.col(column) < 0.0)
        ).height:
            raise ValueError(f"{column} cannot be negative.")
