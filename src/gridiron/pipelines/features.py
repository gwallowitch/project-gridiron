"""Feature-store pipelines for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.features.team_game import build_team_game_features
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.validation.team_game_features import (
    validate_team_game_features,
)


class TeamGameFeaturePipeline(BasePipeline):
    """Build the curated team-game feature dataset for one season."""

    def __init__(
        self,
        *,
        season: int,
        project_root: Path | str = Path("."),
        database_path: Path | str | None = None,
    ) -> None:
        self.paths = ProjectPaths.from_root(project_root)

        catalog_path = (
            Path(database_path)
            if database_path is not None
            else self.paths.metadata_database
        )

        super().__init__(
            season=season,
            database_path=catalog_path,
        )

    @property
    def pipeline_name(self) -> str:
        return "Team-Game Feature Pipeline"

    @property
    def dataset_name(self) -> str:
        return "team_game_features"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.team_game_features_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        input_path = self.paths.play_by_play_file(self.season)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Play-by-play file does not exist: {input_path}"
            )

        self.set_stage("loading")
        play_by_play = pl.read_parquet(input_path)

        self.set_stage("feature engineering")
        features = build_team_game_features(play_by_play)

        self.set_stage("feature validation")
        validate_team_game_features(features)

        self.set_stage("persistence")
        _write_parquet_atomically(
            features,
            self.expected_output_path,
        )

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )


def build_team_game_feature_store(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the team-game feature pipeline."""
    pipeline = TeamGameFeaturePipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    )

    return pipeline.run()


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
