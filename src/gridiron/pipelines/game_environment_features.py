"""Step 82A game-environment feature pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.features.game_environment import build_game_environment_features
from gridiron.pipelines.base import BasePipeline, PipelineArtifact, PipelineRunResult
from gridiron.validation.game_environment_features import (
    validate_game_environment_features,
)


class GameEnvironmentFeaturesPipeline(BasePipeline):
    """Build and persist historical environment features."""

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
        super().__init__(season=season, database_path=catalog_path)

    @property
    def pipeline_name(self) -> str:
        return "Game Environment Features Pipeline"

    @property
    def dataset_name(self) -> str:
        return "game_environment_features"

    @property
    def expected_output_path(self) -> Path:
        return (
            self.paths.root
            / "data"
            / "curated"
            / "game_environment_features"
            / f"game_environment_features_{self.season}.parquet"
        )

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        schedule_path = self.paths.schedule_file(self.season)
        if not schedule_path.exists():
            raise FileNotFoundError(
                f"Schedule file does not exist: {schedule_path}"
            )

        self.set_stage("loading")
        schedule = pl.read_parquet(schedule_path)

        self.set_stage("feature calculation")
        features = build_game_environment_features(schedule)

        self.set_stage("feature validation")
        validate_game_environment_features(features)

        self.set_stage("persistence")
        write_parquet_atomically(features, self.expected_output_path)

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )


def run_game_environment_features_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    return GameEnvironmentFeaturesPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    ).run()
