from __future__ import annotations

import polars as pl

from gridiron.ratings.weekly_metrics import (
    build_weekly_team_metrics,
)


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [
                "g1",
                "g2",
                "g1",
                "g2",
            ],
            "week": [
                1,
                2,
                1,
                2,
            ],
            "team": [
                "A",
                "A",
                "B",
                "B",
            ],
            "opponent": [
                "B",
                "B",
                "A",
                "A",
            ],
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


def test_weekly_metrics_returns_two_weeks() -> None:
    result = build_weekly_team_metrics(
        sample_feature_store()
    )

    assert result["week"].unique().to_list() == [1, 2]
    assert result.height == 4


def test_week_two_is_cumulative() -> None:
    result = build_weekly_team_metrics(
        sample_feature_store()
    )

    week_two = result.filter(
        (pl.col("team") == "A")
        & (pl.col("week") == 2)
    )

    assert week_two.item(
        0,
        "offensive_plays",
    ) == 120