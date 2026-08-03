"""Shared execution framework for Project Gridiron pipelines."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from gridiron.data.metadata import record_ingestion

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineArtifact:
    """Persisted data product created by a pipeline."""

    output_path: Path
    row_count: int
    column_count: int

    @property
    def file_size_bytes(self) -> int:
        """Return the persisted artifact size."""
        if not self.output_path.exists():
            return 0

        return self.output_path.stat().st_size


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Summary of a successful pipeline execution."""

    pipeline_name: str
    dataset: str
    season: int
    artifact: PipelineArtifact
    elapsed_seconds: float
    run_id: str

    @property
    def rows_per_second(self) -> float:
        """Return processing throughput for the completed run."""
        if self.elapsed_seconds <= 0:
            return 0.0

        return self.artifact.row_count / self.elapsed_seconds


class PipelineExecutionError(RuntimeError):
    """Raised when a pipeline fails during execution."""

    def __init__(
        self,
        *,
        pipeline_name: str,
        season: int,
        stage: str,
        reason: str,
    ) -> None:
        self.pipeline_name = pipeline_name
        self.season = season
        self.stage = stage
        self.reason = reason

        super().__init__(
            f"{pipeline_name} failed for season {season} "
            f"during {stage}: {reason}"
        )


class BasePipeline(ABC):
    """Execute, audit, and report one Project Gridiron pipeline."""

    def __init__(
        self,
        *,
        season: int,
        database_path: Path | str,
    ) -> None:
        _validate_season(season)

        self.season = season
        self.database_path = Path(database_path)
        self._current_stage = "initialization"

    @property
    @abstractmethod
    def pipeline_name(self) -> str:
        """Human-readable pipeline name."""

    @property
    @abstractmethod
    def dataset_name(self) -> str:
        """Metadata catalog dataset identifier."""

    @property
    @abstractmethod
    def expected_output_path(self) -> Path:
        """Canonical output location, including before execution."""

    @abstractmethod
    def execute(self) -> PipelineArtifact:
        """Perform pipeline-specific work and return its artifact."""

    def set_stage(self, stage: str) -> None:
        """Update the stage reported if the pipeline fails."""
        if not stage.strip():
            raise ValueError("Pipeline stage cannot be empty.")

        self._current_stage = stage

    def run(self) -> PipelineRunResult:
        """Run the pipeline and register its outcome in DuckDB."""
        started_at = perf_counter()

        LOGGER.info(
            "Pipeline started: %s, season=%s",
            self.pipeline_name,
            self.season,
        )

        try:
            self.set_stage("execution")
            artifact = self.execute()

            self.set_stage("artifact validation")
            self._validate_artifact(artifact)

            elapsed_seconds = perf_counter() - started_at

            self.set_stage("metadata registration")
            run_id = record_ingestion(
                database_path=self.database_path,
                dataset=self.dataset_name,
                season=self.season,
                row_count=artifact.row_count,
                column_count=artifact.column_count,
                file_path=artifact.output_path,
                file_size_bytes=artifact.file_size_bytes,
                status="success",
            )
        except Exception as exc:
            elapsed_seconds = perf_counter() - started_at
            self._record_failure(exc)

            LOGGER.exception(
                "Pipeline failed: %s, season=%s, stage=%s",
                self.pipeline_name,
                self.season,
                self._current_stage,
            )

            if isinstance(exc, PipelineExecutionError):
                raise

            raise PipelineExecutionError(
                pipeline_name=self.pipeline_name,
                season=self.season,
                stage=self._current_stage,
                reason=str(exc),
            ) from exc

        LOGGER.info(
            "Pipeline completed: %s, season=%s, rows=%s, "
            "elapsed_seconds=%.3f",
            self.pipeline_name,
            self.season,
            artifact.row_count,
            elapsed_seconds,
        )

        return PipelineRunResult(
            pipeline_name=self.pipeline_name,
            dataset=self.dataset_name,
            season=self.season,
            artifact=artifact,
            elapsed_seconds=elapsed_seconds,
            run_id=run_id,
        )

    def _validate_artifact(self, artifact: PipelineArtifact) -> None:
        if artifact.row_count < 1:
            raise ValueError("Pipeline artifact contains no rows.")

        if artifact.column_count < 1:
            raise ValueError("Pipeline artifact contains no columns.")

        if not artifact.output_path.exists():
            raise FileNotFoundError(
                f"Pipeline artifact does not exist: "
                f"{artifact.output_path}"
            )

        if artifact.file_size_bytes < 1:
            raise ValueError("Pipeline artifact file is empty.")

    def _record_failure(self, error: Exception) -> None:
        try:
            record_ingestion(
                database_path=self.database_path,
                dataset=self.dataset_name,
                season=self.season,
                row_count=0,
                column_count=0,
                file_path=self.expected_output_path,
                file_size_bytes=0,
                status="failed",
                error_message=(
                    f"{type(error).__name__}: {error}"
                ),
            )
        except Exception:
            LOGGER.exception(
                "Could not register failed pipeline run: %s",
                self.pipeline_name,
            )


def _validate_season(season: int) -> None:
    if season < 1999 or season > 2100:
        raise ValueError(
            "NFL seasons must be between 1999 and 2100."
        )
