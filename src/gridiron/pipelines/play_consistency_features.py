"""Step 87A play-consistency feature pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.features.play_consistency import (
    build_play_consistency_features,
)
from gridiron.pipelines.base import (
    BasePipeline,
    PipelineArtifact,
    PipelineRunResult,
)
from gridiron.validation.play_consistency_features import (
    validate_play_consistency_features,
)


class PlayConsistencyFeaturesPipeline(BasePipeline):
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
        return "Play Consistency Features Pipeline"

    @property
    def dataset_name(self) -> str:
        return "play_consistency_features"

    @property
    def expected_output_path(self) -> Path:
        return (
            self.paths.root
            / "data"
            / "curated"
            / "play_consistency_features"
            / f"play_consistency_features_{self.season}.parquet"
        )

    def execute(self) -> PipelineArtifact:
        schedule_path = self.paths.schedule_file(self.season)
        pbp_path = self.paths.play_by_play_file(self.season)

        if not schedule_path.exists():
            raise FileNotFoundError(schedule_path)
        if not pbp_path.exists():
            raise FileNotFoundError(pbp_path)

        schedule = pl.read_parquet(schedule_path)
        pbp = pl.read_parquet(pbp_path)

        features = build_play_consistency_features(schedule, pbp)
        validate_play_consistency_features(features)

        write_parquet_atomically(
            features,
            self.expected_output_path,
        )

        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=features.height,
            column_count=len(features.columns),
        )


def run_play_consistency_features_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> PipelineRunResult:
    return PlayConsistencyFeaturesPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    ).run()
