from __future__ import annotations

from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.research.models import (
    ResearchRun,
    SeasonResearchResult,
)
from gridiron.research.report import format_research_report


def result() -> ExperimentResult:
    return ExperimentResult.create(
        config=ExperimentConfig(
            name="baseline",
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
        selection_score=0.47,
    )


def test_report_contains_run_summary() -> None:
    run = ResearchRun(
        profile="modern",
        seasons=(2025,),
        experiment_count=1,
        total_runs=1,
        runtime_seconds=0.5,
        generated_at="now",
        git_commit=None,
        python_version="3.13",
        results=(
            SeasonResearchResult(
                season=2025,
                experiments=(result(),),
            ),
        ),
    )

    report = format_research_report(run)

    assert "PROJECT GRIDIRON RESEARCH" in report
    assert "modern" in report
    assert "best=baseline" in report
