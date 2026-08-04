from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.core.paths import ProjectPaths


def test_project_paths_resolve_from_root(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    assert paths.root == tmp_path.resolve()
    assert paths.data == tmp_path.resolve() / "data"
    assert paths.raw == tmp_path.resolve() / "data" / "raw"
    assert paths.curated == tmp_path.resolve() / "data" / "curated"
    assert paths.metadata_database == (
        tmp_path.resolve() / "database" / "gridiron.duckdb"
    )


def test_project_paths_build_dataset_files(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    assert paths.schedule_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "raw"
        / "schedules"
        / "schedules_2025.parquet"
    )
    assert paths.play_by_play_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "raw"
        / "play_by_play"
        / "play_by_play_2025.parquet"
    )
    assert paths.team_game_features_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "curated"
        / "team_game_features"
        / "team_game_features_2025.parquet"
    )
    assert paths.team_ratings_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "curated"
        / "team_ratings"
        / "team_ratings_2025.parquet"
    )
    assert paths.weekly_team_ratings_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "curated"
        / "weekly_team_ratings"
        / "weekly_team_ratings_2025.parquet"
    )
    assert paths.strength_of_schedule_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "curated"
        / "strength_of_schedule"
        / "strength_of_schedule_2025.parquet"
    )
    assert paths.pgr_file(2025) == (
        tmp_path.resolve()
        / "data"
        / "curated"
        / "pgr"
        / "pgr_2025.parquet"
    )


def test_project_paths_reject_invalid_season(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    with pytest.raises(ValueError, match="between 1999 and 2100"):
        paths.schedule_file(1998)


def test_create_runtime_directories(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    paths.create_runtime_directories()

    assert paths.schedules.is_dir()
    assert paths.play_by_play.is_dir()
    assert paths.team_game_features.is_dir()
    assert paths.team_ratings.is_dir()
    assert paths.weekly_team_ratings.is_dir()
    assert paths.strength_of_schedule.is_dir()
    assert paths.pgr.is_dir()
    assert paths.database.is_dir()
    assert paths.output.is_dir()
