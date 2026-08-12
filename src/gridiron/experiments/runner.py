"""Configuration-driven prediction experiment runner."""
from __future__ import annotations

import polars as pl

from gridiron.backtest.evaluator import evaluate_predictions
from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.validation import validate_experiments
from gridiron.prediction.confidence import classify_confidence
from gridiron.prediction.engine import build_predictions
from gridiron.prediction.probability import home_win_probability

_REQUIRED_REST_COLUMNS=frozenset({"game_id","rest_advantage"})
_REQUIRED_QB_COLUMNS=frozenset({"game_id","qb_rating_difference"})
_REQUIRED_INJURY_COLUMNS=frozenset({
    "game_id","injury_score_difference","source_timestamp_available",
})

def run_experiments(
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    experiments: list[ExperimentConfig],
    rest_features: pl.DataFrame|None=None,
    qb_features: pl.DataFrame|None=None,
    injury_features: pl.DataFrame|None=None,
) -> list[ExperimentResult]:
    validate_experiments(experiments)
    _validate_input(experiments,rest_features,qb_features,injury_features)
    results=[
        _run_one(schedule,pgr,rest_features,qb_features,injury_features,c)
        for c in experiments
    ]
    return sorted(results,key=lambda r:(
        r.selection_score,r.brier_score,r.log_loss,-r.winner_accuracy,r.name
    ))

def _run_one(schedule,pgr,rest_features,qb_features,injury_features,config):
    predictions=build_predictions(
        schedule,pgr,
        home_field_advantage=config.home_field_advantage,
        probability_scale=config.probability_scale,
    )
    predictions=_join_or_zero(predictions,rest_features,"rest_advantage")
    predictions=_join_or_zero(predictions,qb_features,"qb_rating_difference")
    predictions=_join_or_zero(
        predictions,injury_features,"injury_score_difference"
    )
    predictions=(
        predictions.with_columns(
            (
                pl.col("rating_difference")
                + pl.col("rest_advantage")*config.rest_weight
                + pl.col("qb_rating_difference")*config.qb_weight
                - pl.col("injury_score_difference")*config.injury_weight
            ).alias("rating_difference")
        )
        .with_columns(
            (
                pl.col("rating_difference")*config.margin_scale
                + config.margin_intercept
            ).alias("expected_home_margin"),
            pl.col("rating_difference").map_elements(
                lambda value: home_win_probability(
                    value,scale=config.probability_scale
                ),
                return_dtype=pl.Float64,
            ).alias("home_win_probability"),
        )
        .with_columns(
            (1.0-pl.col("home_win_probability"))
            .alias("away_win_probability"),
            pl.when(pl.col("rating_difference")>=0)
            .then(pl.col("home_team"))
            .otherwise(pl.col("away_team"))
            .alias("predicted_winner"),
            pl.col("home_win_probability").map_elements(
                classify_confidence,return_dtype=pl.String
            ).alias("confidence"),
            pl.lit(config.name).alias("model_version"),
        )
    )
    for column,label in (
        ("rest_advantage","Rest"),
        ("qb_rating_difference","QB"),
        ("injury_score_difference","Injury"),
    ):
        if predictions[column].null_count():
            raise ValueError(
                f"{label} features do not cover every prediction game."
            )
    backtest,_=evaluate_predictions(predictions,schedule)
    score=selection_score(
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_rmse=backtest.margin_rmse,
    )
    return ExperimentResult.create(
        config=config,season=backtest.season,
        games_evaluated=backtest.games_evaluated,
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_mae=backtest.margin_mae,
        margin_rmse=backtest.margin_rmse,
        selection_score=score,
    )

def _join_or_zero(predictions,features,column):
    if features is None:
        return predictions.with_columns(pl.lit(0.0).alias(column))
    return predictions.join(
        features.select("game_id",column),
        on="game_id",how="left",validate="1:1",
    )

def _validate_input(experiments,rest_features,qb_features,injury_features):
    _validate_feature(
        experiments,rest_features,_REQUIRED_REST_COLUMNS,
        "rest_weight","Rest"
    )
    _validate_feature(
        experiments,qb_features,_REQUIRED_QB_COLUMNS,
        "qb_weight","QB"
    )
    _validate_feature(
        experiments,injury_features,_REQUIRED_INJURY_COLUMNS,
        "injury_weight","Injury"
    )
    if (
        injury_features is not None
        and any(e.injury_weight != 0.0 for e in experiments)
        and not bool(
            injury_features["source_timestamp_available"].all()
        )
    ):
        raise ValueError(
            "Injury experiments require timestamp-available features."
        )
def _validate_feature(experiments,features,required,weight_attr,label):
    if any(getattr(e,weight_attr)!=0.0 for e in experiments) and features is None:
        raise ValueError(
            f"{label} features are required for non-zero {weight_attr}."
        )
    if features is None:
        return
    missing=required.difference(features.columns)
    if missing:
        raise ValueError(
            f"{label} features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if features["game_id"].n_unique()!=features.height:
        raise ValueError(f"{label} features contain duplicate game rows.")

def selection_score(*,winner_accuracy,brier_score,log_loss,margin_rmse):
    return (
        brier_score+0.25*log_loss+0.01*margin_rmse-0.10*winner_accuracy
    )
