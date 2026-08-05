from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.prediction.pipeline import run_prediction_pipeline


def write_inputs(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.schedules.mkdir(parents=True)
    paths.pgr.mkdir(parents=True)
    pl.DataFrame({
        "game_id": ["g1"],
        "season": [2025],
        "week": [1],
        "away_team": ["A"],
        "home_team": ["B"],
    }).write_parquet(paths.schedule_file(2025))
    pl.DataFrame({
        "season": [2025, 2025],
        "week": [1, 1],
        "team": ["A", "B"],
        "pgr_rating": [101.0, 99.0],
    }).write_parquet(paths.pgr_file(2025))
    return paths


def test_prediction_pipeline_persists_and_registers(tmp_path: Path) -> None:
    paths = write_inputs(tmp_path)
    result = run_prediction_pipeline(2025, project_root=tmp_path)
    assert result.dataset == "predictions"
    assert result.artifact.row_count == 1
    assert paths.predictions_file(2025).exists()
    records = read_ingestion_log(paths.metadata_database)
    assert len(records) == 1
    assert records[0]["status"] == "success"


def test_prediction_pipeline_records_missing_input(tmp_path: Path) -> None:
    with pytest.raises(PipelineExecutionError, match="input validation"):
        run_prediction_pipeline(2025, project_root=tmp_path)
