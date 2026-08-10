from __future__ import annotations

import pytest

from gridiron.experiments.models import (
    ExperimentConfig,
    ExperimentResult,
)
from gridiron.research.baseline import resolve_baseline_name
from gridiron.research.models import (
    ResearchRun,
    SeasonResearchResult,
)


def result(name: str) -> ExperimentResult:
    return ExperimentResult.create(
        config=ExperimentConfig(
            name=name,
            home_field_advantage=1.5,
            probability_scale=0.14,
        ),
        season=2025,
        games_evaluated=1,
        winner_accuracy=1.0,
        brier_score=0.1,
        log_loss=0.1,
        margin_mae=1.0,
        margin_rmse=1.0,
        selection_score=0.1,
    )


def run(names: tuple[str, ...]) -> ResearchRun:
    return ResearchRun(
        profile="test",
        seasons=(2025,),
        experiment_count=len(names),
        total_runs=len(names),
        runtime_seconds=0.0,
        generated_at="now",
        git_commit=None,
        python_version="3.13",
        results=(
            SeasonResearchResult(
                season=2025,
                experiments=tuple(result(name) for name in names),
            ),
        ),
    )


def test_infers_qb_baseline() -> None:
    assert resolve_baseline_name(
        run(("qb_000_baseline", "qb_025"))
    ) == "qb_000_baseline"


def test_rejects_multiple_baselines() -> None:
    with pytest.raises(ValueError, match="Multiple baseline"):
        resolve_baseline_name(
            run(("a_baseline", "b_baseline"))
        )
