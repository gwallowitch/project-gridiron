"""Evaluation services for Project Gridiron rating benchmarks."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import polars as pl

from gridiron.benchmark.metrics import rating_distribution, weekly_movement
from gridiron.benchmark.models import BenchmarkResult
from gridiron.core.paths import ProjectPaths
from gridiron.pgr.validation import validate_pgr


def evaluate_pgr(frame: pl.DataFrame) -> BenchmarkResult:
    """Evaluate a validated PGR dataset and return its health metrics."""
    started_at = perf_counter()
    validate_pgr(frame)

    seasons = frame["season"].unique().sort().to_list()
    if len(seasons) != 1:
        raise ValueError("A benchmark must contain exactly one season.")

    versions = frame["model_version"].unique().sort().to_list()
    if len(versions) != 1:
        raise ValueError("A benchmark must contain exactly one model version.")

    distribution = rating_distribution(frame)
    movement = weekly_movement(frame)

    return BenchmarkResult(
        season=int(seasons[0]),
        model_version=str(versions[0]),
        team_count=frame["team"].n_unique(),
        week_count=frame["week"].n_unique(),
        row_count=frame.height,
        league_average=distribution["league_average"],
        median_rating=distribution["median_rating"],
        standard_deviation=distribution["standard_deviation"],
        minimum_rating=distribution["minimum_rating"],
        maximum_rating=distribution["maximum_rating"],
        rating_spread=distribution["rating_spread"],
        average_weekly_movement=float(
            movement["average_weekly_movement"]
        ),
        maximum_weekly_movement=float(
            movement["maximum_weekly_movement"]
        ),
        movement_observations=int(movement["movement_observations"]),
        runtime_seconds=perf_counter() - started_at,
    )


def evaluate_pgr_season(
    season: int,
    *,
    project_root: Path | str = Path("."),
) -> BenchmarkResult:
    """Load and evaluate the persisted PGR dataset for one season."""
    paths = ProjectPaths.from_root(project_root)
    input_path = paths.pgr_file(season)

    if not input_path.exists():
        raise FileNotFoundError(f"PGR file does not exist: {input_path}")

    return evaluate_pgr(pl.read_parquet(input_path))
