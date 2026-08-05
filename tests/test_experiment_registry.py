from __future__ import annotations

from pathlib import Path

from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.registry import append_registry, load_registry


def result(name: str) -> ExperimentResult:
    return ExperimentResult.create(
        config=ExperimentConfig(name, 1.5, 0.18),
        season=2025,
        games_evaluated=10,
        winner_accuracy=0.6,
        brier_score=0.24,
        log_loss=0.69,
        margin_mae=10.0,
        margin_rmse=13.0,
        selection_score=0.48,
    )


def test_registry_round_trip_and_append(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"

    append_registry(path, [result("one")])
    append_registry(path, [result("two")])

    records = load_registry(path)
    assert [record["name"] for record in records] == ["one", "two"]


def test_missing_registry_is_empty(tmp_path: Path) -> None:
    assert load_registry(tmp_path / "missing.json") == []
