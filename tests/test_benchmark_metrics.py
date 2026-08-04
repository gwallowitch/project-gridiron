from __future__ import annotations

import polars as pl
import pytest

from gridiron.benchmark.metrics import rating_distribution, weekly_movement


def sample_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "team": ["A", "B", "A", "B"],
            "week": [1, 1, 2, 2],
            "pgr_rating": [98.0, 102.0, 101.0, 99.0],
        }
    )


def test_rating_distribution_calculates_expected_values() -> None:
    result = rating_distribution(sample_frame())

    assert result["league_average"] == pytest.approx(100.0)
    assert result["median_rating"] == pytest.approx(100.0)
    assert result["minimum_rating"] == 98.0
    assert result["maximum_rating"] == 102.0
    assert result["rating_spread"] == 4.0
    assert result["standard_deviation"] == pytest.approx(
        2.5**0.5
    )


def test_weekly_movement_calculates_absolute_changes() -> None:
    result = weekly_movement(sample_frame())

    assert result["movement_observations"] == 2
    assert result["average_weekly_movement"] == pytest.approx(3.0)
    assert result["maximum_weekly_movement"] == pytest.approx(3.0)


def test_weekly_movement_returns_zero_without_prior_weeks() -> None:
    result = weekly_movement(sample_frame().filter(pl.col("week") == 1))

    assert result["movement_observations"] == 0
    assert result["average_weekly_movement"] == 0.0
    assert result["maximum_weekly_movement"] == 0.0


def test_metrics_reject_empty_frames() -> None:
    empty = sample_frame().head(0)

    with pytest.raises(ValueError, match="empty PGR dataset"):
        rating_distribution(empty)

    with pytest.raises(ValueError, match="empty PGR dataset"):
        weekly_movement(empty)
