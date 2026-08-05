from __future__ import annotations

import pytest

from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.report import format_experiment_report


def sample_result() -> ExperimentResult:
    return ExperimentResult.create(
        config=ExperimentConfig("baseline", 1.5, 0.18),
        season=2025,
        games_evaluated=284,
        winner_accuracy=0.609,
        brier_score=0.2426,
        log_loss=0.6936,
        margin_mae=10.753,
        margin_rmse=13.582,
        selection_score=0.49,
    )


def test_report_contains_rank_and_recommendation() -> None:
    report = format_experiment_report([sample_result()])

    assert "PROJECT GRIDIRON EXPERIMENTS" in report
    assert "baseline" in report
    assert "Recommended configuration: baseline" in report


def test_report_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="empty"):
        format_experiment_report([])
