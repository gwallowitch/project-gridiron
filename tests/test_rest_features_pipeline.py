from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.rest_features import (
    RestFeaturesPipeline,
    run_rest_features_pipeline,
)


def write_schedule(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.schedules.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "gameday": ["2025-09-04"],
            "home_team": ["A"],
            "away_team": ["B"],
        }
    ).write_parquet(paths.schedule_file(2025))
    return paths


def test_pipeline_properties(tmp_path: Path) -> None:
    pipeline = RestFeaturesPipeline(
        season=2025,
        project_root=tmp_path,
    )

    assert pipeline.pipeline_name == "Rest Features Pipeline"
    assert pipeline.dataset_name == "rest_features"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).rest_features_file(2025)
    )


def test_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = write_schedule(tmp_path)

    result = run_rest_features_pipeline(
        2025,
        project_root=tmp_path,
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 1

    saved = pl.read_parquet(result.artifact.output_path)
    assert saved["rest_advantage"].to_list() == [0]

    records = read_ingestion_log(paths.metadata_database)
    assert len(records) == 1
    assert records[0]["dataset"] == "rest_features"
    assert records[0]["status"] == "success"


def test_pipeline_records_missing_input_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during input validation",
    ):
        run_rest_features_pipeline(
            2025,
            project_root=tmp_path,
        )

    records = read_ingestion_log(paths.metadata_database)
    assert len(records) == 1
    assert records[0]["dataset"] == "rest_features"
    assert records[0]["status"] == "failed"
