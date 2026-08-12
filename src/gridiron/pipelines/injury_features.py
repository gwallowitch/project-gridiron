"""Standalone injury availability feature pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.data.parquet import write_parquet_atomically
from gridiron.features.injuries import (
    build_game_injury_features,
    normalize_injury_reports,
)
from gridiron.pipelines.base import BasePipeline, PipelineArtifact, PipelineRunResult
from gridiron.validation.injury_features import validate_injury_features


class InjuryFeaturesPipeline(BasePipeline):
    def __init__(
        self, *, season: int, project_root: Path | str = Path("."),
        database_path: Path | str | None = None, gateway: NFLVerseGateway | None = None,
    ) -> None:
        self.paths = ProjectPaths.from_root(project_root)
        self.gateway = gateway or NFLVerseGateway()
        catalog_path = Path(database_path) if database_path is not None else self.paths.metadata_database
        super().__init__(season=season, database_path=catalog_path)

    @property
    def pipeline_name(self) -> str:
        return "Injury Features Pipeline"

    @property
    def dataset_name(self) -> str:
        return "injury_features"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.injury_features_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        schedule_path = self.paths.schedule_file(self.season)
        if not schedule_path.exists():
            raise FileNotFoundError(f"Schedule file does not exist: {schedule_path}")

        self.set_stage("loading")
        schedule = pl.read_parquet(schedule_path)
        raw_injuries = self.gateway.injuries([self.season])

        self.set_stage("normalization")
        injuries = normalize_injury_reports(raw_injuries)

        self.set_stage("feature calculation")
        features = build_game_injury_features(schedule, injuries)

        self.set_stage("feature validation")
        validate_injury_features(features)

        self.set_stage("persistence")
        write_parquet_atomically(features, self.expected_output_path)
        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )

def run_injury_features_pipeline(
    season: int, *, project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    return InjuryFeaturesPipeline(
        season=season, project_root=project_root, database_path=database_path
    ).run()
