"""Pure benchmark metrics for Project Gridiron ratings."""

from __future__ import annotations

import polars as pl


def rating_distribution(frame: pl.DataFrame) -> dict[str, float]:
    """Calculate distribution statistics for the PGR rating column."""
    if frame.height == 0:
        raise ValueError("Cannot benchmark an empty PGR dataset.")

    ratings = frame["pgr_rating"]
    minimum = float(ratings.min())
    maximum = float(ratings.max())

    return {
        "league_average": float(ratings.mean()),
        "median_rating": float(ratings.median()),
        "standard_deviation": float(ratings.std(ddof=0) or 0.0),
        "minimum_rating": minimum,
        "maximum_rating": maximum,
        "rating_spread": maximum - minimum,
    }


def weekly_movement(frame: pl.DataFrame) -> dict[str, float | int]:
    """Calculate absolute team rating changes between observed weeks."""
    if frame.height == 0:
        raise ValueError("Cannot benchmark an empty PGR dataset.")

    movements = (
        frame.sort(["team", "week"])
        .with_columns(
            pl.col("pgr_rating")
            .shift(1)
            .over("team")
            .alias("previous_rating")
        )
        .with_columns(
            (pl.col("pgr_rating") - pl.col("previous_rating"))
            .abs()
            .alias("weekly_movement")
        )
        .drop_nulls("weekly_movement")
    )

    if movements.height == 0:
        return {
            "average_weekly_movement": 0.0,
            "maximum_weekly_movement": 0.0,
            "movement_observations": 0,
        }

    return {
        "average_weekly_movement": float(
            movements["weekly_movement"].mean()
        ),
        "maximum_weekly_movement": float(
            movements["weekly_movement"].max()
        ),
        "movement_observations": movements.height,
    }
