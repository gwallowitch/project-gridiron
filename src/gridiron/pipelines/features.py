"""Feature-store pipelines for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import record_ingestion
from gridiron.features.team_game import build_team_game_features
from gridiron.validation.team_game_features import (
    validate_team_game_features,
)


@dataclass(frozen=True, slots=True)
class FeaturePipelineResult:
    """Summary of one completed feature-store build."""

    season: int
    output_path: Path
    row_count: int
    column_count: int
    file_size_bytes: int
    run_id: str


def build_team_game_feature_store(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> FeaturePipelineResult:
    """Build, validate, persist, and register team-game features."""
    paths = ProjectPaths.from_root(project_root)
    input_path = paths.play_by_play_file(season)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Play-by-play file does not exist: {input_path}"
        )

    play_by_play = pl.read_parquet(input_path)
    features = build_team_game_features(play_by_play)
    validate_team_game_features(features)

    output_path = paths.team_game_features_file(season)
    _write_parquet_atomically(features, output_path)

    catalog_path = (
        Path(database_path)
        if database_path is not None
        else paths.metadata_database
    )

    file_size = output_path.stat().st_size

    run_id = record_ingestion(
        database_path=catalog_path,
        dataset="team_game_features",
        season=season,
        row_count=features.height,
        column_count=len(features.columns),
        file_path=output_path,
        file_size_bytes=file_size,
    )

    return FeaturePipelineResult(
        season=season,
        output_path=output_path,
        row_count=features.height,
        column_count=len(features.columns),
        file_size_bytes=file_size,
        run_id=run_id,
    )


def _write_parquet_atomically(
    frame: pl.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".parquet.tmp")

    try:
        frame.write_parquet(
            temporary_path,
            compression="zstd",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
