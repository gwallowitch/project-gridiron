from __future__ import annotations

import polars as pl
import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments, selection_score


def sample_schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2025, 2025],
            "week": [2, 2],
            "away_team": ["B", "D"],
            "home_team": ["A", "C"],
            "away_score": [17, 24],
            "home_score": [24, 20],
        }
    )


def sample_pgr() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 1, 1],
            "team": ["A", "B", "C", "D"],
            "pgr_rating": [105.0, 100.0, 101.0, 103.0],
        }
    )


def test_run_experiments_returns_ranked_results() -> None:
    configs = [
        ExperimentConfig("steep", 1.5, 0.30),
        ExperimentConfig("gentle", 1.5, 0.10),
    ]

    results = run_experiments(sample_schedule(), sample_pgr(), configs)

    assert len(results) == 2
    assert results[0].selection_score <= results[1].selection_score
    assert {result.name for result in results} == {"steep", "gentle"}


def test_margin_scale_changes_margin_error() -> None:
    configs = [
        ExperimentConfig("full", 1.5, 0.18, margin_scale=1.0),
        ExperimentConfig("half", 1.5, 0.18, margin_scale=0.5),
    ]

    results = run_experiments(sample_schedule(), sample_pgr(), configs)
    by_name = {result.name: result for result in results}

    assert by_name["full"].margin_rmse != by_name["half"].margin_rmse


def test_selection_score_is_lower_for_better_metrics() -> None:
    better = selection_score(
        winner_accuracy=0.65,
        brier_score=0.20,
        log_loss=0.60,
        margin_rmse=12.0,
    )
    worse = selection_score(
        winner_accuracy=0.55,
        brier_score=0.25,
        log_loss=0.72,
        margin_rmse=14.0,
    )

    assert better < worse


def test_runner_rejects_empty_configurations() -> None:
    with pytest.raises(ValueError, match="At least one"):
        run_experiments(sample_schedule(), sample_pgr(), [])
