from __future__ import annotations

import json
from pathlib import Path

from gridiron.benchmark.history import append_benchmark_history
from gridiron.benchmark.models import BenchmarkResult


def sample_result() -> BenchmarkResult:
    return BenchmarkResult(
        season=2025,
        model_version="v1",
        team_count=32,
        week_count=18,
        row_count=576,
        league_average=100.0,
        median_rating=100.0,
        standard_deviation=6.0,
        minimum_rating=85.0,
        maximum_rating=115.0,
        rating_spread=30.0,
        average_weekly_movement=1.5,
        maximum_weekly_movement=7.0,
        movement_observations=544,
        runtime_seconds=0.1,
    )


def test_append_benchmark_history_writes_json_line(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "history" / "benchmarks.jsonl"

    append_benchmark_history(sample_result(), output_path)

    record = json.loads(output_path.read_text(encoding="utf-8"))
    assert record["season"] == 2025
    assert record["model_version"] == "v1"


def test_append_benchmark_history_appends_records(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "benchmarks.jsonl"

    append_benchmark_history(sample_result(), output_path)
    append_benchmark_history(sample_result(), output_path)

    assert len(output_path.read_text(encoding="utf-8").splitlines()) == 2
