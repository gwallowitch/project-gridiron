"""Historical backtesting pipeline."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.backtest.evaluator import evaluate_predictions
from gridiron.backtest.models import BacktestResult
from gridiron.backtest.report import write_backtest_reports
from gridiron.backtest.validation import validate_backtest_games
from gridiron.core.paths import ProjectPaths
from gridiron.data.parquet import write_parquet_atomically
from gridiron.pipelines.base import BasePipeline, PipelineArtifact, PipelineRunResult


class BacktestPipeline(BasePipeline):
    """Evaluate historical predictions against completed game results."""

    def __init__(
        self,
        *,
        season: int,
        project_root: Path | str = Path("."),
        database_path: Path | str | None = None,
    ) -> None:
        self.paths = ProjectPaths.from_root(project_root)
        self.result: BacktestResult | None = None
        catalog_path = (
            Path(database_path)
            if database_path is not None
            else self.paths.metadata_database
        )
        super().__init__(season=season, database_path=catalog_path)

    @property
    def pipeline_name(self) -> str:
        return "Historical Backtest Pipeline"

    @property
    def dataset_name(self) -> str:
        return "backtests"

    @property
    def expected_output_path(self) -> Path:
        return self.paths.backtest_file(self.season)

    def execute(self) -> PipelineArtifact:
        self.set_stage("input validation")
        predictions_path = self.paths.predictions_file(self.season)
        schedule_path = self.paths.schedule_file(self.season)
        if not predictions_path.exists():
            raise FileNotFoundError(
                f"Prediction file does not exist: {predictions_path}"
            )
        if not schedule_path.exists():
            raise FileNotFoundError(f"Schedule file does not exist: {schedule_path}")

        self.set_stage("loading")
        predictions = pl.read_parquet(predictions_path)
        schedule = pl.read_parquet(schedule_path)

        self.set_stage("evaluation")
        result, evaluated_games = evaluate_predictions(predictions, schedule)
        self.result = result

        self.set_stage("validation")
        validate_backtest_games(evaluated_games)

        self.set_stage("persistence")
        write_parquet_atomically(evaluated_games, self.expected_output_path)
        write_backtest_reports(result, self.paths.backtest_reports)
        return PipelineArtifact(
            output_path=self.expected_output_path,
            row_count=evaluated_games.height,
            column_count=len(evaluated_games.columns),
        )


def run_backtest_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
) -> tuple[PipelineRunResult, BacktestResult]:
    """Run a historical backtest and return pipeline and metric results."""
    pipeline = BacktestPipeline(
        season=season,
        project_root=project_root,
        database_path=database_path,
    )
    run_result = pipeline.run()
    if pipeline.result is None:
        raise RuntimeError("Backtest pipeline completed without metrics.")
    return run_result, pipeline.result
