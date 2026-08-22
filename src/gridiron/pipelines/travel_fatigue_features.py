"""Step 81A travel-fatigue feature pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.features.travel_fatigue import build_travel_fatigue_features
from gridiron.pipelines.base import BasePipeline, PipelineArtifact, PipelineRunResult
from gridiron.validation.travel_fatigue_features import (
    validate_travel_fatigue_features,
)


class TravelFatigueFeaturesPipeline(BasePipeline):
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
        return "Travel Fatigue Features Pipeline"

    @property
    def dataset_name(self) -> str:
        return "travel_fatigue_features"

    @property
    def expected_output_path(self) -> Path:
        return (
            self.paths.root
            / "data"
            / "curated"
            / "travel_fatigue_features"
            / f"travel_fatigue_features_{self.season}.parquet"
        )

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        schedule_path = self.paths.schedule_file(self.season)
        if not schedule_path.exists():
            raise FileNotFoundError(f"Schedule file does not exist: {schedule_path}")

        self.set_stage("loading")
        schedule = pl.read_parquet(schedule_path)
        rest_path = self.paths.rest_features_file(self.season)
        rest_features = pl.read_parquet(rest_path) if rest_path.exists() else None

        self.set_stage("feature calculation")
        features = build_travel_fatigue_features(schedule, rest_features)

        self.set_stage("feature validation")
        validate_travel_fatigue_features(features)

        self.set_stage("persistence")
        write_parquet_atomically(features, self.expected_output_path)

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )


def run_travel_fatigue_features_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    return TravelFatigueFeaturesPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    ).run()
