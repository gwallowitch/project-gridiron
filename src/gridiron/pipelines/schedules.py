"""Schedule ingestion pipeline for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

from gridiron.core.paths import ProjectPaths
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.data.persistence import persist_schedule
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.validation.schedules import validate_schedule


class SchedulePipeline(BasePipeline):
    """Download, validate, and persist one NFL schedule season."""

    def __init__(
        self,
        *,
        season: int,
        project_root: Path | str = Path("."),
        database_path: Path | str | None = None,
        gateway: NFLVerseGateway | None = None,
    ) -> None:
        self.paths = ProjectPaths.from_root(project_root)
        self.gateway = gateway or NFLVerseGateway()

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
        return "Schedule Pipeline"

    @property
    def dataset_name(self) -> str:
        return "schedules"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.schedule_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("download")
        schedule = self.gateway.schedules([self.season])

        self.set_stage("validation")
        validate_schedule(schedule)

        season_rows = schedule.filter(
            schedule["season"] == self.season
        )

        if season_rows.height == 0:
            raise ValueError(
                f"Schedule data contains no rows for season {self.season}."
            )

        self.set_stage("persistence")
        output_path = persist_schedule(
            schedule,
            self.season,
            self.paths.data,
        )

        return PipelineArtifact(
            output_path=output_path,
            row_count=season_rows.height,
            column_count=len(season_rows.columns),
        )


def run_schedule_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
    gateway: NFLVerseGateway | None = None,
) -> PipelineRunResult:
    """Run the schedule ingestion pipeline."""
    pipeline = SchedulePipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )

    return pipeline.run()
