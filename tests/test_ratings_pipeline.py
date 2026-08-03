from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.ratings import (
    TeamRatingsPipeline,
    run_team_ratings_pipeline,
)


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g1", "g3", "g2", "g3"],
            "team": ["A", "A", "B", "B", "C", "C"],
            "opponent": ["B", "C", "A", "C", "A", "B"],
            "offensive_plays": [50, 70, 60, 60, 55, 65],
            "offensive_yards": [
                350.0,
                490.0,
                330.0,
                360.0,
                275.0,
                325.0,
            ],
            "offensive_epa": [10.0, 14.0, 4.0, 5.0, -4.0, -5.0],
            "offensive_success_rate": [
                0.52,
                0.54,
                0.45,
                0.46,
                0.38,
                0.40,
            ],
            "explosive_play_rate": [
                0.18,
                0.20,
                0.12,
                0.13,
                0.07,
                0.08,
            ],
            "turnovers": [0, 1, 1, 1, 2, 2],
            "takeaways": [2, 2, 1, 1, 0, 0],
            "defensive_epa_allowed_per_play": [
                -0.12,
                -0.10,
                0.00,
                0.02,
                0.12,
                0.14,
            ],
            "defensive_success_rate_allowed": [
                0.36,
                0.38,
                0.43,
                0.44,
                0.49,
                0.50,
            ],
            "defensive_explosive_play_rate_allowed": [
                0.07,
                0.08,
                0.12,
                0.13,
                0.17,
                0.18,
            ],
        }
    )


def write_feature_store(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.team_game_features.mkdir(parents=True)

    sample_feature_store().write_parquet(
        paths.team_game_features_file(2025)
    )

    return paths


def test_ratings_pipeline_properties(tmp_path: Path) -> None:
    pipeline = TeamRatingsPipeline(
        season=2025,
        project_root=tmp_path,
    )

    assert pipeline.pipeline_name == "Team Ratings Pipeline"
    assert pipeline.dataset_name == "team_ratings"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).team_ratings_file(2025)
    )


def test_ratings_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = write_feature_store(tmp_path)

    result = run_team_ratings_pipeline(
        2025,
        project_root=tmp_path,
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 3
    assert result.artifact.column_count == 7
    assert result.dataset == "team_ratings"
    assert result.run_id

    saved = pl.read_parquet(result.artifact.output_path)

    assert saved.height == 3
    assert saved["team"].to_list() == ["A", "B", "C"]
    assert saved["overall_rating"].mean() == pytest.approx(100.0)

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "team_ratings"
    assert records[0]["status"] == "success"
    assert records[0]["row_count"] == 3


def test_ratings_pipeline_records_missing_input_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during input validation",
    ):
        run_team_ratings_pipeline(
            2025,
            project_root=tmp_path,
        )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "team_ratings"
    assert records[0]["status"] == "failed"


def test_ratings_pipeline_supports_custom_database(
    tmp_path: Path,
) -> None:
    write_feature_store(tmp_path)
    database_path = tmp_path / "custom" / "metadata.duckdb"

    result = run_team_ratings_pipeline(
        2025,
        project_root=tmp_path,
        database_path=database_path,
    )

    assert result.run_id
    assert database_path.exists()
