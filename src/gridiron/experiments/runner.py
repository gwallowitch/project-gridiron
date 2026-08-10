"""Configuration-driven prediction experiment runner."""
from __future__ import annotations

import polars as pl

from gridiron.backtest.evaluator import evaluate_predictions
from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.validation import validate_experiments
from gridiron.prediction.confidence import classify_confidence
from gridiron.prediction.engine import build_predictions
from gridiron.prediction.probability import home_win_probability

_REQUIRED_REST_COLUMNS = frozenset({"game_id", "rest_advantage"})
_REQUIRED_QB_COLUMNS = frozenset({"game_id", "qb_rating_difference"})

def run_experiments(schedule: pl.DataFrame, pgr: pl.DataFrame,
                    experiments: list[ExperimentConfig],
                    rest_features: pl.DataFrame | None = None,
                    qb_features: pl.DataFrame | None = None) -> list[ExperimentResult]:
    """Run, backtest, and rank prediction configurations."""
    validate_experiments(experiments)
    _validate_input(experiments, rest_features, qb_features)
    results = [_run_one(schedule, pgr, rest_features, qb_features, config)
               for config in experiments]
    return sorted(results, key=lambda r: (
        r.selection_score, r.brier_score, r.log_loss,
        -r.winner_accuracy, r.name))

def _run_one(schedule: pl.DataFrame, pgr: pl.DataFrame,
             rest_features: pl.DataFrame | None,
             qb_features: pl.DataFrame | None,
             config: ExperimentConfig) -> ExperimentResult:
    predictions = build_predictions(
        schedule, pgr,
        home_field_advantage=config.home_field_advantage,
        probability_scale=config.probability_scale,
    )
    if rest_features is not None:
        predictions = predictions.join(
            rest_features.select("game_id", "rest_advantage"),
            on="game_id", how="left", validate="1:1")
    else:
        predictions = predictions.with_columns(
            pl.lit(0.0).alias("rest_advantage"))
    if qb_features is not None:
        predictions = predictions.join(
            qb_features.select("game_id", "qb_rating_difference"),
            on="game_id", how="left", validate="1:1")
    else:
        predictions = predictions.with_columns(
            pl.lit(0.0).alias("qb_rating_difference"))

    predictions = (
        predictions.with_columns(
            (pl.col("rating_difference")
             + pl.col("rest_advantage") * config.rest_weight
             + pl.col("qb_rating_difference") * config.qb_weight)
            .alias("rating_difference"))
        .with_columns(
            (pl.col("rating_difference") * config.margin_scale
             + config.margin_intercept).alias("expected_home_margin"),
            pl.col("rating_difference").map_elements(
                lambda value: home_win_probability(
                    value, scale=config.probability_scale),
                return_dtype=pl.Float64).alias("home_win_probability"))
        .with_columns(
            (1.0 - pl.col("home_win_probability")).alias("away_win_probability"),
            pl.when(pl.col("rating_difference") >= 0)
            .then(pl.col("home_team")).otherwise(pl.col("away_team"))
            .alias("predicted_winner"),
            pl.col("home_win_probability").map_elements(
                classify_confidence, return_dtype=pl.String).alias("confidence"),
            pl.lit(config.name).alias("model_version"))
    )
    if predictions["rest_advantage"].null_count():
        raise ValueError("Rest features do not cover every prediction game.")
    if predictions["qb_rating_difference"].null_count():
        raise ValueError("QB features do not cover every prediction game.")

    backtest, _ = evaluate_predictions(predictions, schedule)
    score = selection_score(
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score, log_loss=backtest.log_loss,
        margin_rmse=backtest.margin_rmse)
    return ExperimentResult.create(
        config=config, season=backtest.season,
        games_evaluated=backtest.games_evaluated,
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score, log_loss=backtest.log_loss,
        margin_mae=backtest.margin_mae, margin_rmse=backtest.margin_rmse,
        selection_score=score)

def _validate_input(experiments, rest_features, qb_features) -> None:
    if any(e.rest_weight != 0.0 for e in experiments) and rest_features is None:
        raise ValueError("Rest features are required for non-zero rest weights.")
    if rest_features is not None:
        missing = _REQUIRED_REST_COLUMNS.difference(rest_features.columns)
        if missing:
            raise ValueError(f"Rest features are missing columns: {', '.join(sorted(missing))}")
        if rest_features["game_id"].n_unique() != rest_features.height:
            raise ValueError("Rest features contain duplicate game rows.")
    if any(e.qb_weight != 0.0 for e in experiments) and qb_features is None:
        raise ValueError("QB features are required for non-zero QB weights.")
    if qb_features is not None:
        missing = _REQUIRED_QB_COLUMNS.difference(qb_features.columns)
        if missing:
            raise ValueError(f"QB features are missing columns: {', '.join(sorted(missing))}")
        if qb_features["game_id"].n_unique() != qb_features.height:
            raise ValueError("QB features contain duplicate game rows.")

def selection_score(*, winner_accuracy: float, brier_score: float,
                    log_loss: float, margin_rmse: float) -> float:
    """Return a lower-is-better multi-metric experiment score."""
    return brier_score + 0.25 * log_loss + 0.01 * margin_rmse - 0.10 * winner_accuracy
