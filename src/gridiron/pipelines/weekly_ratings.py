"""Weekly team-rating pipeline for Project Gridiron."""

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
from gridiron.ratings.weekly import build_weekly_team_ratings
from gridiron.ratings.weekly_metrics import build_weekly_team_metrics
from gridiron.validation.weekly_team_ratings import (
    validate_weekly_team_ratings,
)


class WeeklyTeamRatingsPipeline(BasePipeline):
    """Build and persist cumulative team ratings by week."""

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
        return "Weekly Team Ratings Pipeline"

    @property
    def dataset_name(self) -> str:
        return "weekly_team_ratings"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.weekly_team_ratings_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        input_path = self.paths.team_game_features_file(self.season)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Team-game feature file does not exist: {input_path}"
            )

        self.set_stage("loading")
        feature_store = pl.read_parquet(input_path)

        self.set_stage("weekly metric aggregation")
        weekly_metrics = build_weekly_team_metrics(feature_store)

        self.set_stage("weekly rating calculation")
        weekly_ratings = build_weekly_team_ratings(
            weekly_metrics,
            season=self.season,
        )

        self.set_stage("weekly rating validation")
        validate_weekly_team_ratings(weekly_ratings)

        self.set_stage("persistence")
        write_parquet_atomically(
            weekly_ratings,
            self.expected_output_path,
        )

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=weekly_ratings.height,
            column_count=len(weekly_ratings.columns),
        )


def run_weekly_team_ratings_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the weekly team-ratings pipeline."""
    pipeline = WeeklyTeamRatingsPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    )

    return pipeline.run()
