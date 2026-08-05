"""Configuration-driven prediction experiment runner."""

from __future__ import annotations

import polars as pl

from gridiron.backtest.evaluator import evaluate_predictions
from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.validation import validate_experiments
from gridiron.prediction.engine import build_predictions


def run_experiments(
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    experiments: list[ExperimentConfig],
) -> list[ExperimentResult]:
    """Run, backtest, and rank prediction configurations."""
    validate_experiments(experiments)
    results = [
        _run_one(schedule=schedule, pgr=pgr, config=config)
        for config in experiments
    ]
    return sorted(
        results,
        key=lambda result: (
            result.selection_score,
            result.brier_score,
            result.log_loss,
            -result.winner_accuracy,
            result.name,
        ),
    )


def _run_one(
    *,
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    config: ExperimentConfig,
) -> ExperimentResult:
    predictions = build_predictions(
        schedule,
        pgr,
        home_field_advantage=config.home_field_advantage,
        probability_scale=config.probability_scale,
    ).with_columns(
        (
            pl.col("rating_difference") * config.margin_scale
            + config.margin_intercept
        ).alias("expected_home_margin"),
        pl.lit(config.name).alias("model_version"),
    )

    backtest, _ = evaluate_predictions(predictions, schedule)
    score = selection_score(
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_rmse=backtest.margin_rmse,
    )
    return ExperimentResult.create(
        config=config,
        season=backtest.season,
        games_evaluated=backtest.games_evaluated,
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_mae=backtest.margin_mae,
        margin_rmse=backtest.margin_rmse,
        selection_score=score,
    )


def selection_score(
    *,
    winner_accuracy: float,
    brier_score: float,
    log_loss: float,
    margin_rmse: float,
) -> float:
    """Return a lower-is-better multi-metric experiment score."""
    return (
        brier_score
        + 0.25 * log_loss
        + 0.01 * margin_rmse
        - 0.10 * winner_accuracy
    )
