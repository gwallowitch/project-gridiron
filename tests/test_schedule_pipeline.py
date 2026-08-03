from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.schedules import (
    SchedulePipeline,
    run_schedule_pipeline,
)


class FakeGateway:
    def schedules(self, seasons: list[int]) -> pl.DataFrame:
        season = seasons[0]

        return pl.DataFrame(
            {
                "game_id": [f"{season}_01_A_B"],
                "season": [season],
                "week": [1],
                "game_type": ["REG"],
                "gameday": [f"{season}-09-01"],
                "away_team": ["A"],
                "home_team": ["B"],
            }
        )


class EmptyGateway:
    def schedules(self, seasons: list[int]) -> pl.DataFrame:
        return FakeGateway().schedules(seasons).head(0)


def test_schedule_pipeline_properties(tmp_path: Path) -> None:
    pipeline = SchedulePipeline(
        season=2025,
        project_root=tmp_path,
        gateway=FakeGateway(),
    )

    assert pipeline.pipeline_name == "Schedule Pipeline"
    assert pipeline.dataset_name == "schedules"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).schedule_file(2025)
    )


def test_schedule_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    result = run_schedule_pipeline(
        2025,
        project_root=tmp_path,
        gateway=FakeGateway(),
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 1
    assert result.artifact.column_count == 7
    assert result.dataset == "schedules"
    assert result.run_id

    saved = pl.read_parquet(result.artifact.output_path)

    assert saved.height == 1
    assert saved["season"].to_list() == [2025]

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "schedules"
    assert records[0]["status"] == "success"


def test_schedule_pipeline_records_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during validation",
    ):
        run_schedule_pipeline(
            2025,
            project_root=tmp_path,
            gateway=EmptyGateway(),
        )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "schedules"
    assert records[0]["status"] == "failed"


def test_schedule_pipeline_supports_custom_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "custom" / "metadata.duckdb"

    result = run_schedule_pipeline(
        2025,
        project_root=tmp_path,
        database_path=database_path,
        gateway=FakeGateway(),
    )

    assert result.run_id
    assert database_path.exists()
