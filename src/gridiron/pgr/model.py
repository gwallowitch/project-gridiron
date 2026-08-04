"""Project Gridiron Rating version 1 mathematics."""

from __future__ import annotations

import polars as pl

from gridiron.pgr.constants import (
    PGR_MODEL_VERSION,
    RATING_CENTER,
    SCHEDULE_WEIGHT,
)

_REQUIRED_WEEKLY_RATING_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "games_played",
        "overall_rating",
    }
)

_REQUIRED_SOS_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "strength_of_schedule_rating",
    }
)


def build_pgr(
    weekly_ratings: pl.DataFrame,
    strength_of_schedule: pl.DataFrame,
    *,
    schedule_weight: float = SCHEDULE_WEIGHT,
) -> pl.DataFrame:
    """Build PGR v1 from weekly performance and schedule strength.

    PGR v1 is defined as::

        performance_rating
        + schedule_weight * (strength_of_schedule_rating - 100)

    The inputs are joined by season, week, and team. The calculation is
    deterministic and contains no market information or future data beyond
    what is already encoded in the leak-free upstream datasets.
    """
    _validate_inputs(
        weekly_ratings,
        strength_of_schedule,
        schedule_weight=schedule_weight,
    )

    return (
        weekly_ratings.select(
            "season",
            "week",
            "team",
            "games_played",
            pl.col("overall_rating").alias("performance_rating"),
        )
        .join(
            strength_of_schedule.select(
                "season",
                "week",
                "team",
                "strength_of_schedule_rating",
            ),
            on=["season", "week", "team"],
            how="inner",
            validate="1:1",
        )
        .with_columns(
            (
                schedule_weight
                * (
                    pl.col("strength_of_schedule_rating")
                    - RATING_CENTER
                )
            ).alias("schedule_adjustment")
        )
        .with_columns(
            (
                pl.col("performance_rating")
                + pl.col("schedule_adjustment")
            ).alias("pgr_rating"),
            pl.lit(PGR_MODEL_VERSION).alias("model_version"),
        )
        .select(
            "season",
            "week",
            "team",
            "games_played",
            "performance_rating",
            "strength_of_schedule_rating",
            "schedule_adjustment",
            "pgr_rating",
            "model_version",
        )
        .sort(
            ["week", "pgr_rating", "team"],
            descending=[False, True, False],
        )
    )


def _validate_inputs(
    weekly_ratings: pl.DataFrame,
    strength_of_schedule: pl.DataFrame,
    *,
    schedule_weight: float,
) -> None:
    missing_ratings = _REQUIRED_WEEKLY_RATING_COLUMNS.difference(
        weekly_ratings.columns
    )
    if missing_ratings:
        missing_text = ", ".join(sorted(missing_ratings))
        raise ValueError(
            "Weekly ratings are missing required columns: "
            f"{missing_text}"
        )

    missing_sos = _REQUIRED_SOS_COLUMNS.difference(
        strength_of_schedule.columns
    )
    if missing_sos:
        missing_text = ", ".join(sorted(missing_sos))
        raise ValueError(
            "Strength-of-schedule data is missing required columns: "
            f"{missing_text}"
        )

    if weekly_ratings.height == 0:
        raise ValueError("Weekly ratings contain no rows.")

    if strength_of_schedule.height == 0:
        raise ValueError("Strength-of-schedule data contains no rows.")

    if not 0.0 <= schedule_weight <= 1.0:
        raise ValueError("Schedule weight must be between 0.0 and 1.0.")

    rating_keys = weekly_ratings.select("season", "week", "team")
    sos_keys = strength_of_schedule.select("season", "week", "team")

    if rating_keys.n_unique() != weekly_ratings.height:
        raise ValueError("Weekly ratings contain duplicate team-week rows.")

    if sos_keys.n_unique() != strength_of_schedule.height:
        raise ValueError(
            "Strength-of-schedule data contains duplicate team-week rows."
        )

    joined_count = rating_keys.join(
        sos_keys,
        on=["season", "week", "team"],
        how="inner",
    ).height

    if (
        weekly_ratings.height != strength_of_schedule.height
        or joined_count != weekly_ratings.height
    ):
        raise ValueError(
            "Weekly ratings and strength-of-schedule rows do not align."
        )
