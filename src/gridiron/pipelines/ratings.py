"""Team-rating pipeline for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.ratings.metrics import build_team_metrics
from gridiron.ratings.team import build_team_ratings
from gridiron.validation.team_ratings import validate_team_ratings


class TeamRatingsPipeline(BasePipeline):
    """Build and persist team ratings for one NFL season."""

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
        return "Team Ratings Pipeline"

    @property
    def dataset_name(self) -> str:
        return "team_ratings"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.team_ratings_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        input_path = self.paths.team_game_features_file(self.season)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Team-game feature file does not exist: {input_path}"
            )

        self.set_stage("loading")
        feature_store = pl.read_parquet(input_path)

        self.set_stage("metric aggregation")
        team_metrics = build_team_metrics(feature_store)

        self.set_stage("rating calculation")
        team_ratings = build_team_ratings(team_metrics)

        self.set_stage("rating validation")
        validate_team_ratings(team_ratings)

        self.set_stage("persistence")
        _write_parquet_atomically(
            team_ratings,
            self.expected_output_path,
        )

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=team_ratings.height,
            column_count=len(team_ratings.columns),
        )


def run_team_ratings_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the team-ratings pipeline."""
    pipeline = TeamRatingsPipeline(
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