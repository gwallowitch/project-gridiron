from __future__ import annotations

import polars as pl

from gridiron.ratings.normalization import (
    normalize_metrics,
)


def test_normalization_produces_rating_columns() -> None:
    frame = pl.DataFrame(
        {
            "team": ["A", "B", "C"],
            "epa": [1.0, 2.0, 3.0],
            "turnovers": [5, 3, 1],
        }
    )

    result = normalize_metrics(
        frame,
        {
            "epa": True,
            "turnovers": False,
        },
    )

    assert "epa_rating" in result.columns
    assert "turnovers_rating" in result.columns

    ratings = result["epa_rating"]

    assert abs(ratings.mean() - 100.0) < 1e-9