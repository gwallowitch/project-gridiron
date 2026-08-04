from __future__ import annotations

from gridiron.benchmark.models import BenchmarkResult
from gridiron.benchmark.report import format_benchmark_report


def sample_result() -> BenchmarkResult:
    return BenchmarkResult(
        season=2025,
        model_version="v1",
        team_count=32,
        week_count=18,
        row_count=576,
        league_average=100.0,
        median_rating=99.8,
        standard_deviation=6.2,
        minimum_rating=84.0,
        maximum_rating=116.0,
        rating_spread=32.0,
        average_weekly_movement=1.4,
        maximum_weekly_movement=7.2,
        movement_observations=544,
        runtime_seconds=0.125,
    )


def test_report_contains_key_benchmark_values() -> None:
    report = format_benchmark_report(sample_result())

    assert "PROJECT GRIDIRON BENCHMARK" in report
    assert "Season................... 2025" in report
    assert "Model.................... PGR v1" in report
    assert "Teams.................... 32" in report
    assert "Rating Spread............ 32.000" in report
    assert "Average Weekly Movement.. 1.400" in report


def test_report_is_deterministic() -> None:
    assert format_benchmark_report(sample_result()) == format_benchmark_report(
        sample_result()
    )
