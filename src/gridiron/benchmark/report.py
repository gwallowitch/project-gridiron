"""Console reporting for Project Gridiron benchmarks."""

from __future__ import annotations

from gridiron.benchmark.models import BenchmarkResult


def format_benchmark_report(result: BenchmarkResult) -> str:
    """Format one benchmark result as a deterministic text report."""
    lines = [
        "=" * 56,
        "PROJECT GRIDIRON BENCHMARK".center(56),
        "=" * 56,
        f"Season................... {result.season}",
        f"Model.................... PGR {result.model_version}",
        f"Teams.................... {result.team_count}",
        f"Weeks.................... {result.week_count}",
        f"Rows..................... {result.row_count}",
        "-" * 56,
        f"League Average........... {result.league_average:.3f}",
        f"Median Rating............ {result.median_rating:.3f}",
        f"Standard Deviation....... {result.standard_deviation:.3f}",
        f"Minimum Rating........... {result.minimum_rating:.3f}",
        f"Maximum Rating........... {result.maximum_rating:.3f}",
        f"Rating Spread............ {result.rating_spread:.3f}",
        "-" * 56,
        f"Average Weekly Movement.. {result.average_weekly_movement:.3f}",
        f"Maximum Weekly Movement.. {result.maximum_weekly_movement:.3f}",
        f"Movement Observations.... {result.movement_observations}",
        f"Runtime.................. {result.runtime_seconds:.4f} s",
        "=" * 56,
    ]
    return "\n".join(lines)


def print_benchmark_report(result: BenchmarkResult) -> None:
    """Print one benchmark report."""
    print(format_benchmark_report(result))
