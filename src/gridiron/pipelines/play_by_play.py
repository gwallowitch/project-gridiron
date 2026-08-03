"""Play-by-play ingestion pipeline for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

from gridiron.core.paths import ProjectPaths
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.data.persistence import persist_play_by_play
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.validation.play_by_play import validate_play_by_play


class PlayByPlayPipeline(BasePipeline):
    """Download, validate, and persist one NFL play-by-play season."""

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
        return "Play-by-Play Pipeline"

    @property
    def dataset_name(self) -> str:
        return "play_by_play"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.play_by_play_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("download")
        play_by_play = self.gateway.play_by_play([self.season])

        self.set_stage("validation")
        validate_play_by_play(play_by_play)

        season_rows = play_by_play.filter(
            play_by_play["season"] == self.season
        )

        if season_rows.height == 0:
            raise ValueError(
                "Play-by-play data contains no rows "
                f"for season {self.season}."
            )

        self.set_stage("persistence")
        output_path = persist_play_by_play(
            play_by_play,
            self.season,
            self.paths.data,
        )

        return PipelineArtifact(
            output_path=output_path,
            row_count=season_rows.height,
            column_count=len(season_rows.columns),
        )


def run_play_by_play_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
    gateway: NFLVerseGateway | None = None,
) -> PipelineRunResult:
    """Run the play-by-play ingestion pipeline."""
    pipeline = PlayByPlayPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )

    return pipeline.run()
