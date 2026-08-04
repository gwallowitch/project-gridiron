from __future__ import annotations

import polars as pl
import pytest

from gridiron.ratings.weekly import build_weekly_team_ratings
from gridiron.ratings.weekly_metrics import build_weekly_team_metrics


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g1", "g2"],
            "week": [1, 2, 1, 2],
            "team": ["A", "A", "B", "B"],
            "opponent": ["B", "B", "A", "A"],
            "offensive_plays": [50, 70, 80, 40],
            "offensive_yards": [300, 490, 330, 390],
            "offensive_epa": [5, 14, 3, 9],
            "offensive_success_rate": [0.40, 0.50, 0.45, 0.55],
            "explosive_play_rate": [0.10, 0.20, 0.12, 0.18],
            "turnovers": [1, 2, 3, 1],
            "takeaways": [2, 1, 1, 2],
            "defensive_epa_allowed_per_play": [
                -0.10,
                0.20,
                0.10,
                -0.20,
            ],
            "defensive_success_rate_allowed": [
                0.35,
                0.45,
                0.50,
                0.40,
            ],
            "defensive_explosive_play_rate_allowed": [
                0.08,
                0.12,
                0.14,
                0.10,
            ],
        }
    )


def test_weekly_ratings_returns_one_row_per_team_week() -> None:
    weekly_metrics = build_weekly_team_metrics(sample_feature_store())

    result = build_weekly_team_ratings(
        weekly_metrics,
        season=2025,
    )

    assert result.height == 4
    assert result["season"].unique().to_list() == [2025]
    assert result["week"].unique().to_list() == [1, 2]
    assert set(result["team"].to_list()) == {"A", "B"}


def test_weekly_ratings_normalize_each_week_independently() -> None:
    weekly_metrics = build_weekly_team_metrics(sample_feature_store())
    result = build_weekly_team_ratings(
        weekly_metrics,
        season=2025,
    )

    weekly_means = (
        result.group_by("week")
        .agg(pl.col("overall_rating").mean().alias("mean_rating"))
        .sort("week")
    )

    assert weekly_means["mean_rating"].to_list() == pytest.approx(
        [100.0, 100.0]
    )


def test_weekly_ratings_preserve_cumulative_games_played() -> None:
    weekly_metrics = build_weekly_team_metrics(sample_feature_store())
    result = build_weekly_team_ratings(
        weekly_metrics,
        season=2025,
    )

    team_a_week_two = result.filter(
        (pl.col("team") == "A") & (pl.col("week") == 2)
    )

    assert team_a_week_two.item(0, "games_played") == 2


def test_weekly_ratings_require_week_column() -> None:
    weekly_metrics = build_weekly_team_metrics(
        sample_feature_store()
    ).drop("week")

    with pytest.raises(
        ValueError,
        match="missing required column: week",
    ):
        build_weekly_team_ratings(
            weekly_metrics,
            season=2025,
        )
