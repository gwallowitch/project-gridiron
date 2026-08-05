from __future__ import annotations

import polars as pl
import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2025, 2025],
            "week": [2, 2],
            "away_team": ["A", "C"],
            "home_team": ["B", "D"],
            "home_score": [24, 17],
            "away_score": [20, 21],
        }
    )


def pgr() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 1, 1],
            "team": ["A", "B", "C", "D"],
            "pgr_rating": [100.0, 100.0, 100.0, 100.0],
        }
    )


def rest_features() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "rest_advantage": [4, -4],
        }
    )


def config(rest_weight: float) -> ExperimentConfig:
    return ExperimentConfig(
        name=f"rest_{rest_weight}",
        home_field_advantage=1.5,
        probability_scale=0.14,
        margin_scale=0.75,
        rest_weight=rest_weight,
    )


def test_zero_rest_weight_matches_baseline_behavior() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [config(0.0)],
        rest_features(),
    )

    assert result[0].rest_weight == 0.0
    assert result[0].games_evaluated == 2


def test_nonzero_rest_weight_requires_rest_features() -> None:
    with pytest.raises(ValueError, match="required"):
        run_experiments(
            schedule(),
            pgr(),
            [config(0.2)],
        )


def test_missing_rest_games_are_rejected() -> None:
    incomplete = rest_features().filter(
        pl.col("game_id") == "g1"
    )
    with pytest.raises(ValueError, match="cover every"):
        run_experiments(
            schedule(),
            pgr(),
            [config(0.2)],
            incomplete,
        )


def test_rest_weight_is_recorded_in_results() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [config(0.3)],
        rest_features(),
    )

    assert result[0].rest_weight == pytest.approx(0.3)
