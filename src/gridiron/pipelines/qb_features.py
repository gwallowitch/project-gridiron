"""Quarterback feature pipeline for Project Gridiron."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.features.qb import (
    build_qb_features,
    load_qb_ratings,
    load_qb_starters,
)
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.validation.qb_features import validate_qb_features


class QBFeaturesPipeline(BasePipeline):
    """Build and persist quarterback features for one season."""

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
        return "QB Features Pipeline"

    @property
    def dataset_name(self) -> str:
        return "qb_features"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.qb_features_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        schedule_path = self.paths.schedule_file(self.season)
        if not schedule_path.exists():
            raise FileNotFoundError(
                f"Schedule file does not exist: {schedule_path}"
            )

        self.set_stage("loading")
        schedule = pl.read_parquet(schedule_path)
        starters = load_qb_starters(
            self.paths.root / "config" / "qb_starters.csv"
        ).filter(pl.col("season") == self.season)
        ratings = load_qb_ratings(
            self.paths.root / "config" / "qb_ratings.csv"
        )

        self.set_stage("feature calculation")
        features = build_qb_features(
            schedule,
            starters,
            ratings,
        )

        self.set_stage("feature validation")
        validate_qb_features(features)

        self.set_stage("persistence")
        write_parquet_atomically(
            features,
            self.expected_output_path,
        )
        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )


def run_qb_features_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the quarterback feature pipeline."""
    return QBFeaturesPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    ).run()
