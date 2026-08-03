from __future__ import annotations

import polars as pl
import pytest

from gridiron.ratings.team import build_team_ratings


def sample_team_metrics() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "team": ["A", "B", "C"],
            "games_played": [17, 17, 17],
            "offensive_epa_per_play": [0.20, 0.05, -0.10],
            "offensive_success_rate": [0.50, 0.45, 0.40],
            "offensive_yards_per_play": [6.5, 5.7, 4.9],
            "explosive_play_rate": [0.16, 0.12, 0.08],
            "defensive_epa_allowed_per_play": [-0.10, 0.00, 0.10],
            "defensive_success_rate_allowed": [0.38, 0.43, 0.48],
            "defensive_explosive_play_rate_allowed": [
                0.08,
                0.12,
                0.16,
            ],
            "turnover_margin": [8, 0, -8],
        }
    )


def test_build_team_ratings_returns_one_row_per_team() -> None:
    result = build_team_ratings(sample_team_metrics())

    assert result.height == 3
    assert set(result["team"].to_list()) == {"A", "B", "C"}


def test_build_team_ratings_centers_categories_near_100() -> None:
    result = build_team_ratings(sample_team_metrics())

    assert result["offense_rating"].mean() == pytest.approx(100.0)
    assert result["defense_rating"].mean() == pytest.approx(100.0)
    assert result["discipline_rating"].mean() == pytest.approx(100.0)
    assert result["overall_rating"].mean() == pytest.approx(100.0)


def test_build_team_ratings_orders_stronger_team_first() -> None:
    result = build_team_ratings(sample_team_metrics())

    assert result["team"].to_list() == ["A", "B", "C"]
    assert result["overall_rating"][0] > result["overall_rating"][1]
    assert result["overall_rating"][1] > result["overall_rating"][2]


def test_build_team_ratings_uses_neutral_situational_score() -> None:
    result = build_team_ratings(sample_team_metrics())

    assert result["situational_rating"].to_list() == [
        100.0,
        100.0,
        100.0,
    ]


def test_build_team_ratings_rejects_missing_columns() -> None:
    incomplete = sample_team_metrics().drop(
        "offensive_epa_per_play"
    )

    with pytest.raises(
        ValueError,
        match="missing required columns: offensive_epa_per_play",
    ):
        build_team_ratings(incomplete)


def test_build_team_ratings_rejects_duplicate_teams() -> None:
    duplicate = pl.concat(
        [
            sample_team_metrics(),
            sample_team_metrics().head(1),
        ]
    )

    with pytest.raises(
        ValueError,
        match="exactly one row per team",
    ):
        build_team_ratings(duplicate)
        