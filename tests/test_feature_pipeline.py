from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.features import (
    TeamGameFeaturePipeline,
    build_team_game_feature_store,
)


def sample_play_by_play() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "play_id": [1, 2, 3, 4],
            "game_id": ["2025_01_A_B"] * 4,
            "season": [2025] * 4,
            "week": [1] * 4,
            "posteam": ["A", "A", "B", "B"],
            "defteam": ["B", "B", "A", "A"],
            "play_type": ["run", "pass", "run", "pass"],
            "epa": [1.0, -0.5, 0.5, 1.5],
            "success": [1.0, 0.0, 1.0, 1.0],
            "yards_gained": [12.0, 5.0, 4.0, 25.0],
            "pass_attempt": [0.0, 1.0, 0.0, 1.0],
            "rush_attempt": [1.0, 0.0, 1.0, 0.0],
            "interception": [0.0, 0.0, 0.0, 0.0],
            "fumble_lost": [0.0, 0.0, 0.0, 0.0],
        }
    )


def write_input_data(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_root(root)
    paths.play_by_play.mkdir(parents=True)

    sample_play_by_play().write_parquet(
        paths.play_by_play_file(2025)
    )

    return paths


def test_feature_pipeline_properties(tmp_path: Path) -> None:
    pipeline = TeamGameFeaturePipeline(
        season=2025,
        project_root=tmp_path,
    )

    assert pipeline.pipeline_name == "Team-Game Feature Pipeline"
    assert pipeline.dataset_name == "team_game_features"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path)
        .team_game_features_file(2025)
    )


def test_feature_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = write_input_data(tmp_path)

    result = build_team_game_feature_store(
        2025,
        project_root=tmp_path,
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 2
    assert result.artifact.column_count > 10
    assert result.artifact.file_size_bytes > 0
    assert result.run_id
    assert result.dataset == "team_game_features"

    saved = pl.read_parquet(result.artifact.output_path)

    assert saved.height == 2
    assert set(saved["team"].to_list()) == {"A", "B"}

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "team_game_features"
    assert records[0]["season"] == 2025
    assert records[0]["row_count"] == 2
    assert records[0]["status"] == "success"


def test_feature_pipeline_rejects_missing_input(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during input validation",
    ):
        build_team_game_feature_store(
            2025,
            project_root=tmp_path,
        )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "team_game_features"
    assert records[0]["status"] == "failed"
    assert "Play-by-play file does not exist" in (
        records[0]["error_message"]
    )


def test_feature_pipeline_supports_custom_database(
    tmp_path: Path,
) -> None:
    write_input_data(tmp_path)
    custom_database = tmp_path / "custom" / "metadata.duckdb"

    result = build_team_game_feature_store(
        2025,
        project_root=tmp_path,
        database_path=custom_database,
    )

    assert result.run_id
    assert custom_database.exists()

    records = read_ingestion_log(custom_database)

    assert len(records) == 1
    assert records[0]["status"] == "success"
