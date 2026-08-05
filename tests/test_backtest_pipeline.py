from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.backtest.pipeline import run_backtest_pipeline
from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError


def write_inputs(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.schedules.mkdir(parents=True)
    paths.predictions.mkdir(parents=True)
    pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "away_team": ["A"],
            "home_team": ["B"],
            "away_score": [17],
            "home_score": [20],
        }
    ).write_parquet(paths.schedule_file(2025))
    pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "away_team": ["A"],
            "home_team": ["B"],
            "predicted_winner": ["B"],
            "expected_home_margin": [3.0],
            "home_win_probability": [0.7],
            "model_version": ["prediction_v1"],
        }
    ).write_parquet(paths.predictions_file(2025))
    return paths


def test_backtest_pipeline_persists_registers_and_reports(tmp_path: Path) -> None:
    paths = write_inputs(tmp_path)
    run_result, metrics = run_backtest_pipeline(2025, project_root=tmp_path)

    assert run_result.dataset == "backtests"
    assert metrics.winner_accuracy == 1.0
    assert paths.backtest_file(2025).exists()
    assert list(paths.backtest_reports.glob("*.json"))
    assert list(paths.backtest_reports.glob("*.md"))
    records = read_ingestion_log(paths.metadata_database)
    assert records[0]["dataset"] == "backtests"
    assert records[0]["status"] == "success"


def test_backtest_pipeline_records_missing_input(tmp_path: Path) -> None:
    with pytest.raises(PipelineExecutionError, match="input validation"):
        run_backtest_pipeline(2025, project_root=tmp_path)
