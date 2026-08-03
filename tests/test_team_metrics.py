from __future__ import annotations

import polars as pl
import pytest

from gridiron.ratings.metrics import build_team_metrics


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "team": ["A", "A", "B", "B"],
            "offensive_plays": [50, 70, 60, 60],
            "offensive_yards": [300.0, 490.0, 330.0, 390.0],
            "offensive_epa": [5.0, 14.0, 3.0, 9.0],
            "offensive_success_rate": [0.40, 0.50, 0.45, 0.55],
            "explosive_play_rate": [0.10, 0.20, 0.12, 0.18],
            "turnovers": [1, 2, 3, 1],
            "takeaways": [2, 1, 1, 2],
            "defensive_epa_allowed_per_play": [
                -0.10,
                0.00,
                0.10,
                0.20,
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


def test_build_team_metrics_aggregates_one_row_per_team() -> None:
    result = build_team_metrics(sample_feature_store())

    assert result.height == 2
    assert result["team"].to_list() == ["A", "B"]


def test_build_team_metrics_calculates_weighted_offense() -> None:
    result = build_team_metrics(sample_feature_store())
    team_a = result.filter(pl.col("team") == "A").row(0, named=True)

    assert team_a["games_played"] == 2
    assert team_a["offensive_plays"] == 120
    assert team_a["offensive_yards"] == 790.0
    assert team_a["offensive_epa"] == 19.0
    assert team_a["offensive_epa_per_play"] == pytest.approx(
        19.0 / 120.0
    )
    assert team_a["offensive_yards_per_play"] == pytest.approx(
        790.0 / 120.0
    )
    assert team_a["offensive_success_rate"] == pytest.approx(
        (0.40 * 50 + 0.50 * 70) / 120
    )


def test_build_team_metrics_calculates_turnover_margin() -> None:
    result = build_team_metrics(sample_feature_store())
    team_a = result.filter(pl.col("team") == "A").row(0, named=True)

    assert team_a["turnovers"] == 3
    assert team_a["takeaways"] == 3
    assert team_a["turnover_margin"] == 0


def test_build_team_metrics_rejects_missing_columns() -> None:
    incomplete = sample_feature_store().drop("offensive_epa")

    with pytest.raises(
        ValueError,
        match="missing required columns: offensive_epa",
    ):
        build_team_metrics(incomplete)