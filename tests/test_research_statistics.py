from __future__ import annotations

import pytest

from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.research.models import ResearchRun, SeasonResearchResult
from gridiron.research.statistics import (
    analyze_candidates,
    bootstrap_mean_interval,
)


def result(name: str, season: int, score: float) -> ExperimentResult:
    return ExperimentResult.create(
        config=ExperimentConfig(
            name=name,
            home_field_advantage=1.5,
            probability_scale=0.14,
            margin_scale=0.75,
            rest_weight=0.0,
        ),
        season=season,
        games_evaluated=100,
        winner_accuracy=0.61,
        brier_score=0.23,
        log_loss=0.66,
        margin_mae=10.5,
        margin_rmse=13.3,
        selection_score=score,
    )


def research_run() -> ResearchRun:
    seasons = (2022, 2023, 2024, 2025)
    return ResearchRun(
        profile="modern",
        seasons=seasons,
        experiment_count=2,
        total_runs=8,
        runtime_seconds=1.0,
        generated_at="now",
        git_commit=None,
        python_version="3.13",
        results=tuple(
            SeasonResearchResult(
                season=season,
                experiments=(
                    result("rest_040", season, 0.468),
                    result("rest_000_baseline", season, 0.470),
                ),
            )
            for season in seasons
        ),
    )


def test_analyzes_paired_deltas() -> None:
    analysis = analyze_candidates(research_run())[0]
    assert analysis.wins == 4
    assert analysis.losses == 0
    assert analysis.mean_score_delta == pytest.approx(-0.002)


def test_bootstrap_is_deterministic() -> None:
    kwargs = {
        "samples": 1000,
        "confidence_level": 0.95,
        "random_seed": 60,
    }
    assert bootstrap_mean_interval([-0.1, -0.2], **kwargs) == (
        bootstrap_mean_interval([-0.1, -0.2], **kwargs)
    )


def test_too_few_bootstrap_samples_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 100"):
        analyze_candidates(research_run(), bootstrap_samples=10)
