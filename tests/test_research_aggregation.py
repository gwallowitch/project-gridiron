from __future__ import annotations

import pytest

from gridiron.experiments.models import (
    ExperimentConfig,
    ExperimentResult,
)
from gridiron.research.aggregation import aggregate_research
from gridiron.research.models import (
    ResearchRun,
    SeasonResearchResult,
)


def experiment(
    name: str,
    season: int,
    *,
    accuracy: float,
    score: float,
) -> ExperimentResult:
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
        winner_accuracy=accuracy,
        brier_score=0.23,
        log_loss=0.66,
        margin_mae=10.5,
        margin_rmse=13.3,
        selection_score=score,
    )


def research_run() -> ResearchRun:
    return ResearchRun(
        profile="modern",
        seasons=(2024, 2025),
        experiment_count=2,
        total_runs=4,
        runtime_seconds=1.0,
        generated_at="now",
        git_commit=None,
        python_version="3.13",
        results=(
            SeasonResearchResult(
                season=2024,
                experiments=(
                    experiment(
                        "rest_010",
                        2024,
                        accuracy=0.62,
                        score=0.44,
                    ),
                    experiment(
                        "rest_000_baseline",
                        2024,
                        accuracy=0.61,
                        score=0.45,
                    ),
                ),
            ),
            SeasonResearchResult(
                season=2025,
                experiments=(
                    experiment(
                        "rest_000_baseline",
                        2025,
                        accuracy=0.61,
                        score=0.47,
                    ),
                    experiment(
                        "rest_010",
                        2025,
                        accuracy=0.60,
                        score=0.48,
                    ),
                ),
            ),
        ),
    )


def test_aggregates_and_ranks_experiments() -> None:
    aggregates = aggregate_research(research_run())

    assert len(aggregates) == 2
    assert aggregates[0].name == "rest_000_baseline"
    assert aggregates[0].average_selection_score == pytest.approx(
        0.46
    )


def test_counts_season_wins() -> None:
    aggregates = {
        item.name: item
        for item in aggregate_research(research_run())
    }

    assert aggregates["rest_010"].season_wins == 1
    assert aggregates["rest_000_baseline"].season_wins == 1


def test_calculates_baseline_delta() -> None:
    aggregates = {
        item.name: item
        for item in aggregate_research(research_run())
    }

    assert aggregates[
        "rest_000_baseline"
    ].baseline_score_delta == pytest.approx(0.0)
    assert aggregates[
        "rest_010"
    ].baseline_score_delta == pytest.approx(0.0)


def test_missing_baseline_is_rejected() -> None:
    run = research_run()
    with pytest.raises(ValueError, match="was not found"):
        aggregate_research(
            run,
            baseline_name="missing",
        )
