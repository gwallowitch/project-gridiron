from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import PipelineExecutionError
from gridiron.pipelines.weekly_ratings import (
    WeeklyTeamRatingsPipeline,
    run_weekly_team_ratings_pipeline,
)


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g1", "g2"],
            "week": [1, 2, 1, 2],
            "team": ["A", "A", "B", "B"],
            "opponent": ["B", "B", "A", "A"],
            "offensive_plays": [50, 70, 80, 40],
            "offensive_yards": [300, 490, 330, 390],
            "offensive_epa": [5, 14, 3, 9],
            "offensive_success_rate": [0.40, 0.50, 0.45, 0.55],
            "explosive_play_rate": [0.10, 0.20, 0.12, 0.18],
            "turnovers": [1, 2, 3, 1],
            "takeaways": [2, 1, 1, 2],
            "defensive_epa_allowed_per_play": [
                -0.10,
                0.20,
                0.10,
                -0.20,
            ],
            "defensive_success_rate_allowed": [
                0.35,
                0.45,
                0.50,
                0.40,
            ],
            "defensive_explosive_play_rate_allowed": [
                0.08,
                0.12,
                0.14,
                0.10,
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


def test_weekly_ratings_pipeline_properties(tmp_path: Path) -> None:
    pipeline = WeeklyTeamRatingsPipeline(
        season=2025,
        project_root=tmp_path,
    )

    assert pipeline.pipeline_name == "Weekly Team Ratings Pipeline"
    assert pipeline.dataset_name == "weekly_team_ratings"
    assert pipeline.expected_output_path == (
        ProjectPaths.from_root(tmp_path).weekly_team_ratings_file(2025)
    )


def test_weekly_ratings_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = write_feature_store(tmp_path)

    result = run_weekly_team_ratings_pipeline(
        2025,
        project_root=tmp_path,
    )

    assert result.artifact.output_path.exists()
    assert result.artifact.row_count == 4
    assert result.artifact.column_count == 9
    assert result.dataset == "weekly_team_ratings"
    assert result.run_id

    saved = pl.read_parquet(result.artifact.output_path)

    assert saved.height == 4
    assert saved["week"].unique().to_list() == [1, 2]
    weekly_means = (
        saved.group_by("week")
        .agg(pl.col("overall_rating").mean().alias("mean_rating"))
        .sort("week")
    )
    assert weekly_means["mean_rating"].to_list() == pytest.approx(
        [100.0, 100.0]
    )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "weekly_team_ratings"
    assert records[0]["status"] == "success"
    assert records[0]["row_count"] == 4


def test_weekly_ratings_pipeline_records_missing_input_failure(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(
        PipelineExecutionError,
        match="during input validation",
    ):
        run_weekly_team_ratings_pipeline(
            2025,
            project_root=tmp_path,
        )

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "weekly_team_ratings"
    assert records[0]["status"] == "failed"


def test_weekly_ratings_pipeline_supports_custom_database(
    tmp_path: Path,
) -> None:
    write_feature_store(tmp_path)
    database_path = tmp_path / "custom" / "metadata.duckdb"

    result = run_weekly_team_ratings_pipeline(
        2025,
        project_root=tmp_path,
        database_path=database_path,
    )

    assert result.run_id
    assert database_path.exists()
