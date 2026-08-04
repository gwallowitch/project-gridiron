from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pgr.pipeline import PGRPipeline, run_pgr_pipeline
from gridiron.pipelines.base import PipelineExecutionError


def write_inputs(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.weekly_team_ratings.mkdir(parents=True)
    paths.strength_of_schedule.mkdir(parents=True)

    pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 2],
            "team": ["A", "B", "A", "B"],
            "games_played": [1, 1, 2, 2],
            "overall_rating": [110.0, 90.0, 108.0, 92.0],
        }
    ).write_parquet(paths.weekly_team_ratings_file(2025))

    pl.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 2],
            "team": ["A", "B", "A", "B"],
            "strength_of_schedule_rating": [
                100.0,
                100.0,
                104.0,
                96.0,
            ],
        }
    ).write_parquet(paths.strength_of_schedule_file(2025))

    return paths


def test_pgr_pipeline_properties(tmp_path: Path) -> None:
    pipeline = PGRPipeline(season=2025, project_root=tmp_path)

    assert pipeline.pipeline_name == "Project Gridiron Rating Pipeline"
    assert pipeline.dataset_name == "pgr"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).pgr_file(2025)
    )


def test_pgr_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = write_inputs(tmp_path)

    result = run_pgr_pipeline(2025, project_root=tmp_path)

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 4
    assert result.artifact.column_count == 9
    assert result.dataset == "pgr"
    assert result.run_id

    saved = pl.read_parquet(result.artifact.output_path)
    assert saved.height == 4
    assert saved["model_version"].unique().to_list() == ["v1"]

    records = read_ingestion_log(paths.metadata_database)
    assert len(records) == 1
    assert records[0]["dataset"] == "pgr"
    assert records[0]["status"] == "success"


def test_pgr_pipeline_records_missing_input_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during input validation",
    ):
        run_pgr_pipeline(2025, project_root=tmp_path)

    records = read_ingestion_log(paths.metadata_database)
    assert len(records) == 1
    assert records[0]["dataset"] == "pgr"
    assert records[0]["status"] == "failed"


def test_pgr_pipeline_supports_custom_database(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    database_path = tmp_path / "custom" / "metadata.duckdb"

    result = run_pgr_pipeline(
        2025,
        project_root=tmp_path,
        database_path=database_path,
    )

    assert result.run_id
    assert database_path.exists()
