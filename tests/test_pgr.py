from __future__ import annotations

import polars as pl
import pytest

from gridiron.pgr.constants import PGR_MODEL_VERSION
from gridiron.pgr.model import build_pgr


def sample_weekly_ratings() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 2],
            "team": ["A", "B", "A", "B"],
            "games_played": [1, 1, 2, 2],
            "overall_rating": [110.0, 90.0, 108.0, 92.0],
        }
    )


def sample_sos() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 2],
            "team": ["A", "B", "A", "B"],
            "strength_of_schedule_rating": [100.0, 100.0, 104.0, 96.0],
        }
    )


def test_pgr_week_one_equals_performance_rating() -> None:
    result = build_pgr(sample_weekly_ratings(), sample_sos())
    week_one = result.filter(pl.col("week") == 1)

    assert week_one["schedule_adjustment"].to_list() == [0.0, 0.0]
    assert week_one["pgr_rating"].to_list() == [110.0, 90.0]


def test_pgr_rewards_stronger_schedule() -> None:
    result = build_pgr(sample_weekly_ratings(), sample_sos())
    team_a = result.filter(
        (pl.col("week") == 2) & (pl.col("team") == "A")
    ).row(0, named=True)

    assert team_a["schedule_adjustment"] == pytest.approx(2.0)
    assert team_a["pgr_rating"] == pytest.approx(110.0)


def test_pgr_penalizes_weaker_schedule() -> None:
    result = build_pgr(sample_weekly_ratings(), sample_sos())
    team_b = result.filter(
        (pl.col("week") == 2) & (pl.col("team") == "B")
    ).row(0, named=True)

    assert team_b["schedule_adjustment"] == pytest.approx(-2.0)
    assert team_b["pgr_rating"] == pytest.approx(90.0)


def test_pgr_supports_explicit_schedule_weight() -> None:
    result = build_pgr(
        sample_weekly_ratings(),
        sample_sos(),
        schedule_weight=0.25,
    )
    team_a = result.filter(
        (pl.col("week") == 2) & (pl.col("team") == "A")
    ).row(0, named=True)

    assert team_a["schedule_adjustment"] == pytest.approx(1.0)
    assert team_a["pgr_rating"] == pytest.approx(109.0)


def test_pgr_records_model_version() -> None:
    result = build_pgr(sample_weekly_ratings(), sample_sos())

    assert result["model_version"].unique().to_list() == [
        PGR_MODEL_VERSION
    ]


def test_pgr_is_deterministic() -> None:
    first = build_pgr(sample_weekly_ratings(), sample_sos())
    second = build_pgr(sample_weekly_ratings(), sample_sos())

    assert first.equals(second)


def test_pgr_rejects_missing_weekly_rating_columns() -> None:
    incomplete = sample_weekly_ratings().drop("overall_rating")

    with pytest.raises(
        ValueError,
        match="missing required columns: overall_rating",
    ):
        build_pgr(incomplete, sample_sos())


def test_pgr_rejects_misaligned_inputs() -> None:
    incomplete_sos = sample_sos().filter(pl.col("team") == "A")

    with pytest.raises(
        ValueError,
        match="rows do not align",
    ):
        build_pgr(sample_weekly_ratings(), incomplete_sos)


def test_pgr_rejects_invalid_schedule_weight() -> None:
    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        build_pgr(
            sample_weekly_ratings(),
            sample_sos(),
            schedule_weight=1.5,
        )
