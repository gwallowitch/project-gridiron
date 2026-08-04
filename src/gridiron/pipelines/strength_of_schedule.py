"""Strength-of-schedule pipeline for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.ratings.strength_of_schedule import (
    build_strength_of_schedule,
)
from gridiron.validation.strength_of_schedule import (
    validate_strength_of_schedule,
)


class StrengthOfSchedulePipeline(BasePipeline):
    """Build and persist weekly strength of schedule."""

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
        return "Strength of Schedule Pipeline"

    @property
    def dataset_name(self) -> str:
        return "strength_of_schedule"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.strength_of_schedule_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        feature_path = self.paths.team_game_features_file(self.season)
        ratings_path = self.paths.weekly_team_ratings_file(self.season)

        if not feature_path.exists():
            raise FileNotFoundError(
                f"Team-game feature file does not exist: {feature_path}"
            )

        if not ratings_path.exists():
            raise FileNotFoundError(
                f"Weekly team-rating file does not exist: {ratings_path}"
            )

        self.set_stage("loading")
        feature_store = pl.read_parquet(feature_path)
        weekly_ratings = pl.read_parquet(ratings_path)

        self.set_stage("schedule calculation")
        schedule_strength = build_strength_of_schedule(
            feature_store,
            weekly_ratings,
        )

        self.set_stage("schedule validation")
        validate_strength_of_schedule(schedule_strength)

        self.set_stage("persistence")
        write_parquet_atomically(
            schedule_strength,
            self.expected_output_path,
        )

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=schedule_strength.height,
            column_count=len(schedule_strength.columns),
        )


def run_strength_of_schedule_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the strength-of-schedule pipeline."""
    pipeline = StrengthOfSchedulePipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    )
    return pipeline.run()
