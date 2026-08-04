"""Validation for strength-of-schedule datasets."""

from __future__ import annotations

import polars as pl

REQUIRED_STRENGTH_OF_SCHEDULE_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "games_played",
        "average_opponent_rating",
        "strength_of_schedule_rating",
    }
)


def validate_strength_of_schedule(frame: pl.DataFrame) -> None:
    """Validate weekly strength-of-schedule output."""
    missing = REQUIRED_STRENGTH_OF_SCHEDULE_COLUMNS.difference(
        frame.columns
    )
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            "Strength-of-schedule data is missing required columns: "
            f"{missing_text}"
        )

    if frame.height < 1:
        raise ValueError("Strength-of-schedule data contains no rows.")

    unique_rows = frame.select(
        pl.struct(["season", "week", "team"]).n_unique()
    ).item()
    if unique_rows != frame.height:
        raise ValueError(
            "Strength-of-schedule data contains duplicate team-week rows."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Strength-of-schedule data contains an invalid week."
        )

    if frame.filter(pl.col("games_played") < 1).height:
        raise ValueError(
            "Strength-of-schedule data contains invalid games played."
        )

    rating_columns = [
        "average_opponent_rating",
        "strength_of_schedule_rating",
    ]

    if any(frame[column].null_count() for column in rating_columns):
        raise ValueError(
            "Strength-of-schedule data contains null ratings."
        )

    non_finite = frame.filter(
        pl.any_horizontal(
            [
                pl.col(column).is_infinite()
                | pl.col(column).is_nan()
                for column in rating_columns
            ]
        )
    )
    if non_finite.height:
        raise ValueError(
            "Strength-of-schedule data contains non-finite ratings."
        )
