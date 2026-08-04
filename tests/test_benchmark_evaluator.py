from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.benchmark.evaluator import evaluate_pgr, evaluate_pgr_season
from gridiron.core.paths import ProjectPaths
from gridiron.pgr.constants import PGR_MODEL_VERSION


def sample_pgr() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 2],
            "team": ["A", "B", "A", "B"],
            "games_played": [1, 1, 2, 2],
            "performance_rating": [98.0, 102.0, 100.0, 100.0],
            "strength_of_schedule_rating": [100.0] * 4,
            "schedule_adjustment": [0.0] * 4,
            "pgr_rating": [98.0, 102.0, 101.0, 99.0],
            "model_version": [PGR_MODEL_VERSION] * 4,
        }
    )


def test_evaluate_pgr_returns_complete_result() -> None:
    result = evaluate_pgr(sample_pgr())

    assert result.season == 2025
    assert result.model_version == PGR_MODEL_VERSION
    assert result.team_count == 2
    assert result.week_count == 2
    assert result.row_count == 4
    assert result.league_average == pytest.approx(100.0)
    assert result.rating_spread == pytest.approx(4.0)
    assert result.average_weekly_movement == pytest.approx(3.0)
    assert result.runtime_seconds >= 0.0


def test_evaluate_pgr_is_deterministic_except_runtime() -> None:
    first = evaluate_pgr(sample_pgr())
    second = evaluate_pgr(sample_pgr())

    assert first.season == second.season
    assert first.league_average == second.league_average
    assert first.standard_deviation == second.standard_deviation
    assert first.average_weekly_movement == second.average_weekly_movement


def test_evaluate_pgr_rejects_multiple_seasons() -> None:
    frame = sample_pgr().with_columns(
        pl.when(pl.col("week") == 2)
        .then(pl.lit(2024))
        .otherwise(pl.col("season"))
        .alias("season")
    )

    with pytest.raises(ValueError, match="exactly one season"):
        evaluate_pgr(frame)


def test_evaluate_pgr_season_reads_persisted_dataset(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)
    paths.pgr.mkdir(parents=True)
    sample_pgr().write_parquet(paths.pgr_file(2025))

    result = evaluate_pgr_season(2025, project_root=tmp_path)

    assert result.season == 2025
    assert result.row_count == 4


def test_evaluate_pgr_season_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="PGR file does not exist"):
        evaluate_pgr_season(2025, project_root=tmp_path)
