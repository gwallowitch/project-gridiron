"""Validation for Project Gridiron Rating datasets."""

from __future__ import annotations

import polars as pl

from gridiron.pgr.constants import PGR_MODEL_VERSION

REQUIRED_PGR_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "games_played",
        "performance_rating",
        "strength_of_schedule_rating",
        "schedule_adjustment",
        "pgr_rating",
        "model_version",
    }
)


def validate_pgr(frame: pl.DataFrame) -> None:
    """Validate one PGR dataset."""
    missing = REQUIRED_PGR_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"PGR data is missing required columns: {missing_text}"
        )

    if frame.height < 1:
        raise ValueError("PGR data contains no rows.")

    unique_rows = frame.select(
        pl.struct(["season", "week", "team"]).n_unique()
    ).item()
    if unique_rows != frame.height:
        raise ValueError("PGR data contains duplicate team-week rows.")

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("PGR data contains an invalid week.")

    if frame.filter(pl.col("games_played") < 1).height:
        raise ValueError("PGR data contains invalid games played.")

    rating_columns = [
        "performance_rating",
        "strength_of_schedule_rating",
        "schedule_adjustment",
        "pgr_rating",
    ]

    if any(frame[column].null_count() for column in rating_columns):
        raise ValueError("PGR data contains null ratings.")

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
        raise ValueError("PGR data contains non-finite ratings.")

    versions = frame["model_version"].unique().to_list()
    if versions != [PGR_MODEL_VERSION]:
        raise ValueError(
            "PGR data contains an unsupported model version."
        )
