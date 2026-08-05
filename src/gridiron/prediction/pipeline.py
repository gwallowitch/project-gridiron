"""Prediction Engine v1 pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.pipelines.base import BasePipeline, PipelineArtifact, PipelineRunResult
from gridiron.prediction.engine import build_predictions
from gridiron.prediction.validation import validate_predictions


class PredictionPipeline(BasePipeline):
    """Build and persist game predictions for one season."""

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
        return "Prediction Engine Pipeline"

    @property
    def dataset_name(self) -> str:
        return "predictions"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.predictions_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        schedule_path = self.paths.schedule_file(self.season)
        pgr_path = self.paths.pgr_file(self.season)
        if not schedule_path.exists():
            raise FileNotFoundError(f"Schedule file does not exist: {schedule_path}")
        if not pgr_path.exists():
            raise FileNotFoundError(f"PGR file does not exist: {pgr_path}")

        self.set_stage("loading")
        schedule = pl.read_parquet(schedule_path)
        pgr = pl.read_parquet(pgr_path)

        self.set_stage("prediction calculation")
        predictions = build_predictions(schedule, pgr)

        self.set_stage("prediction validation")
        validate_predictions(predictions)

        self.set_stage("persistence")
        write_parquet_atomically(predictions, self.expected_output_path)
        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=predictions.height,
            column_count=len(predictions.columns),
        )


def run_prediction_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    """Run the Prediction Engine pipeline."""
    return PredictionPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    ).run()
