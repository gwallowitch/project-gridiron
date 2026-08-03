from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineExecutionError,
)


class SuccessfulPipeline(BasePipeline):
    def __init__(
        self,
        *,
        season: int,
        root: Path,
    ) -> None:
        self.root = root
        super().__init__(
            season=season,
            database_path=root / "database" / "gridiron.duckdb",
        )

    @property
    def pipeline_name(self) -> str:
        return "Successful Test Pipeline"

    @property
    def dataset_name(self) -> str:
        return "test_dataset"

    @property
    def expected_output_path(self) -> Path:
        return self.root / "output" / "test.parquet"

    def execute(self) -> PipelineArtifact:
        self.set_stage("persistence")
        self.expected_output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.expected_output_path.write_bytes(b"test artifact")

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=10,
            column_count=4,
        )


class FailingPipeline(SuccessfulPipeline):
    @property
    def pipeline_name(self) -> str:
        return "Failing Test Pipeline"

    @property
    def dataset_name(self) -> str:
        return "failed_test_dataset"

    def execute(self) -> PipelineArtifact:
        self.set_stage("validation")
        raise ValueError("required column is missing")


def test_pipeline_run_returns_summary(tmp_path: Path) -> None:
    pipeline = SuccessfulPipeline(
        season=2025,
        root=tmp_path,
    )

    result = pipeline.run()

    assert result.pipeline_name == "Successful Test Pipeline"
    assert result.dataset == "test_dataset"
    assert result.season == 2025
    assert result.artifact.row_count == 10
    assert result.artifact.column_count == 4
    assert result.artifact.file_size_bytes > 0
    assert result.elapsed_seconds >= 0
    assert result.run_id
    assert result.rows_per_second >= 0


def test_successful_pipeline_registers_metadata(
    tmp_path: Path,
) -> None:
    pipeline = SuccessfulPipeline(
        season=2025,
        root=tmp_path,
    )

    pipeline.run()

    records = read_ingestion_log(pipeline.database_path)

    assert len(records) == 1
    assert records[0]["dataset"] == "test_dataset"
    assert records[0]["status"] == "success"
    assert records[0]["row_count"] == 10
    assert records[0]["column_count"] == 4


def test_failed_pipeline_raises_structured_error(
    tmp_path: Path,
) -> None:
    pipeline = FailingPipeline(
        season=2025,
        root=tmp_path,
    )

    with pytest.raises(
        PipelineExecutionError,
        match=(
            "Failing Test Pipeline failed for season 2025 "
            "during validation"
        ),
    ):
        pipeline.run()


def test_failed_pipeline_registers_failure(
    tmp_path: Path,
) -> None:
    pipeline = FailingPipeline(
        season=2025,
        root=tmp_path,
    )

    with pytest.raises(PipelineExecutionError):
        pipeline.run()

    records = read_ingestion_log(pipeline.database_path)

    assert len(records) == 1
    assert records[0]["dataset"] == "failed_test_dataset"
    assert records[0]["status"] == "failed"
    assert records[0]["row_count"] == 0
    assert records[0]["error_message"] == (
        "ValueError: required column is missing"
    )


def test_pipeline_rejects_invalid_season(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="between 1999 and 2100",
    ):
        SuccessfulPipeline(
            season=1998,
            root=tmp_path,
        )


def test_pipeline_rejects_missing_artifact(
    tmp_path: Path,
) -> None:
    class MissingArtifactPipeline(SuccessfulPipeline):
        def execute(self) -> PipelineArtifact:
            return PipelineArtifact(
                output_path=self.expected_output_path,
                row_count=10,
                column_count=4,
            )

    pipeline = MissingArtifactPipeline(
        season=2025,
        root=tmp_path,
    )

    with pytest.raises(
        PipelineExecutionError,
        match="artifact validation",
    ):
        pipeline.run()
