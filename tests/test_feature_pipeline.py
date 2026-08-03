from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.features import build_team_game_feature_store


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


def test_feature_pipeline_persists_and_registers_data(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)
    paths.play_by_play.mkdir(parents=True)

    sample_play_by_play().write_parquet(
        paths.play_by_play_file(2025)
    )

    result = build_team_game_feature_store(
        2025,
        project_root=tmp_path,
    )

    assert result.output_path.exists()
    assert result.row_count == 2
    assert result.column_count > 10
    assert result.file_size_bytes > 0
    assert result.run_id

    saved = pl.read_parquet(result.output_path)

    assert saved.height == 2
    assert set(saved["team"].to_list()) == {"A", "B"}

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 1
    assert records[0]["dataset"] == "team_game_features"
    assert records[0]["season"] == 2025
    assert records[0]["row_count"] == 2


def test_feature_pipeline_rejects_missing_input(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Play-by-play file does not exist",
    ):
        build_team_game_feature_store(
            2025,
            project_root=tmp_path,
        )
