"""Validation for quarterback feature datasets."""

from __future__ import annotations

import polars as pl

REQUIRED_QB_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "home_qb",
        "away_qb",
        "home_qb_rating",
        "away_qb_rating",
        "qb_rating_difference",
        "home_qb_known",
        "away_qb_known",
    }
)


def validate_qb_features(frame: pl.DataFrame) -> None:
    """Raise when a quarterback feature dataset is unusable."""
    missing = REQUIRED_QB_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"QB features are missing columns: {missing_text}"
        )
    if frame.height == 0:
        raise ValueError("QB feature dataset contains no games.")
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("QB features contain duplicate game rows.")
    if any(frame.null_count().row(0)):
        raise ValueError("QB features contain null values.")

    invalid = frame.filter(
        pl.col("qb_rating_difference")
        != (
            pl.col("home_qb_rating")
            - pl.col("away_qb_rating")
        )
    )
    if invalid.height:
        raise ValueError(
            "QB rating difference does not match rating inputs."
        )
