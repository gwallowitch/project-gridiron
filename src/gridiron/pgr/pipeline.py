"""Project Gridiron Rating pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.pgr.model import build_pgr
from gridiron.pgr.validation import validate_pgr
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)


class PGRPipeline(BasePipeline):
    """Build and persist Project Gridiron Ratings for one season."""

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
        return "Project Gridiron Rating Pipeline"

    @property
    def dataset_name(self) -> str:
        return "pgr"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.pgr_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        ratings_path = self.paths.weekly_team_ratings_file(self.season)
        sos_path = self.paths.strength_of_schedule_file(self.season)

        if not ratings_path.exists():
            raise FileNotFoundError(
                f"Weekly team-rating file does not exist: {ratings_path}"
            )

        if not sos_path.exists():
            raise FileNotFoundError(
                "Strength-of-schedule file does not exist: "
                f"{sos_path}"
            )

        self.set_stage("loading")
        weekly_ratings = pl.read_parquet(ratings_path)
        strength_of_schedule = pl.read_parquet(sos_path)

        self.set_stage("PGR calculation")
        pgr = build_pgr(weekly_ratings, strength_of_schedule)

        self.set_stage("PGR validation")
        validate_pgr(pgr)

        self.set_stage("persistence")
        write_parquet_atomically(pgr, self.expected_output_path)

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=pgr.height,
            column_count=len(pgr.columns),
        )


def run_pgr_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the Project Gridiron Rating pipeline."""
    pipeline = PGRPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    )
    return pipeline.run()
