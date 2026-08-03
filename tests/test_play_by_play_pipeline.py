from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.play_by_play import (
    PlayByPlayPipeline,
    run_play_by_play_pipeline,
)


class FakeGateway:
    def play_by_play(self, seasons: list[int]) -> pl.DataFrame:
        season = seasons[0]

        return pl.DataFrame(
            {
                "play_id": [1, 2],
                "game_id": [f"{season}_01_A_B"] * 2,
                "season": [season, season],
                "week": [1, 1],
                "posteam": ["A", "B"],
                "defteam": ["B", "A"],
                "play_type": ["run", "pass"],
                "epa": [0.5, -0.2],
                "success": [1.0, 0.0],
                "yards_gained": [8.0, 3.0],
                "pass_attempt": [0.0, 1.0],
                "rush_attempt": [1.0, 0.0],
                "interception": [0.0, 0.0],
                "fumble_lost": [0.0, 0.0],
            }
        )


class EmptyGateway:
    def play_by_play(self, seasons: list[int]) -> pl.DataFrame:
        return FakeGateway().play_by_play(seasons).head(0)


def test_play_by_play_pipeline_properties(
    tmp_path: Path,
) -> None:
    pipeline = PlayByPlayPipeline(
        season=2025,
        project_root=tmp_path,
        gateway=FakeGateway(),
    )

    assert pipeline.pipeline_name == "Play-by-Play Pipeline"
    assert pipeline.dataset_name == "play_by_play"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).play_by_play_file(2025)
    )


def test_play_by_play_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    result = run_play_by_play_pipeline(
        2025,
        project_root=tmp_path,
        gateway=FakeGateway(),
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 2
    assert result.artifact.column_count == 14
    assert result.dataset == "play_by_play"
    assert result.run_id

    saved = pl.read_parquet(result.artifact.output_path)

    assert saved.height == 2
    assert saved["season"].unique().to_list() == [2025]

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "play_by_play"
    assert records[0]["status"] == "success"
    assert records[0]["row_count"] == 2


def test_play_by_play_pipeline_records_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during validation",
    ):
        run_play_by_play_pipeline(
            2025,
            project_root=tmp_path,
            gateway=EmptyGateway(),
        )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "play_by_play"
    assert records[0]["status"] == "failed"


def test_play_by_play_pipeline_supports_custom_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "custom" / "metadata.duckdb"

    result = run_play_by_play_pipeline(
        2025,
        project_root=tmp_path,
        database_path=database_path,
        gateway=FakeGateway(),
    )

    assert result.run_id
    assert database_path.exists()
