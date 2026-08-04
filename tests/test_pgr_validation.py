from __future__ import annotations

import polars as pl
import pytest

from gridiron.pgr.validation import validate_pgr


def valid_pgr() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025],
            "week": [1, 1],
            "team": ["A", "B"],
            "games_played": [1, 1],
            "performance_rating": [110.0, 90.0],
            "strength_of_schedule_rating": [100.0, 100.0],
            "schedule_adjustment": [0.0, 0.0],
            "pgr_rating": [110.0, 90.0],
            "model_version": ["v1", "v1"],
        }
    )


def test_validate_pgr_accepts_valid_data() -> None:
    validate_pgr(valid_pgr())


def test_validate_pgr_rejects_duplicate_rows() -> None:
    duplicate = pl.concat([valid_pgr(), valid_pgr().head(1)])

    with pytest.raises(ValueError, match="duplicate team-week"):
        validate_pgr(duplicate)


def test_validate_pgr_rejects_non_finite_rating() -> None:
    invalid = valid_pgr().with_columns(
        pl.when(pl.col("team") == "A")
        .then(float("nan"))
        .otherwise(pl.col("pgr_rating"))
        .alias("pgr_rating")
    )

    with pytest.raises(ValueError, match="non-finite"):
        validate_pgr(invalid)


def test_validate_pgr_rejects_wrong_model_version() -> None:
    invalid = valid_pgr().with_columns(
        pl.lit("experimental").alias("model_version")
    )

    with pytest.raises(ValueError, match="unsupported model version"):
        validate_pgr(invalid)
