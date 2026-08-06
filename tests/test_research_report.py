from __future__ import annotations

from gridiron.experiments.models import (
    ExperimentConfig,
    ExperimentResult,
)
from gridiron.research.models import (
    ResearchRun,
    SeasonResearchResult,
)
from gridiron.research.report import format_research_report


def result(
    name: str,
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
        season=2025,
        games_evaluated=284,
        winner_accuracy=0.61,
        brier_score=0.23,
        log_loss=0.66,
        margin_mae=10.5,
        margin_rmse=13.3,
        selection_score=score,
    )


def test_report_contains_aggregate_ranking() -> None:
    run = ResearchRun(
        profile="modern",
        seasons=(2025,),
        experiment_count=2,
        total_runs=2,
        runtime_seconds=0.5,
        generated_at="now",
        git_commit=None,
        python_version="3.13",
        results=(
            SeasonResearchResult(
                season=2025,
                experiments=(
                    result("rest_010", 0.46),
                    result("rest_000_baseline", 0.47),
                ),
            ),
        ),
    )

    report = format_research_report(run)

    assert "CROSS-SEASON AGGREGATE RANKING" in report
    assert "PROMOTION REVIEW" in report
    assert "Candidate................. rest_010" in report
    assert "Status.................... INCONCLUSIVE" in report
    assert "DeltaBase" in report
