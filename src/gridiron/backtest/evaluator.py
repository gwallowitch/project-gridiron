"""Historical evaluation engine for persisted predictions."""

from __future__ import annotations

from time import perf_counter

import polars as pl

from gridiron.backtest.calibration import build_calibration_buckets
from gridiron.backtest.metrics import (
    binary_log_loss,
    brier_score,
    mean_absolute_error,
    root_mean_squared_error,
    winner_accuracy,
)
from gridiron.backtest.models import BacktestResult

_REQUIRED_PREDICTION_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "away_team",
        "home_team",
        "predicted_winner",
        "expected_home_margin",
        "home_win_probability",
        "model_version",
    }
)
_REQUIRED_SCHEDULE_COLUMNS = frozenset(
    {"game_id", "season", "away_team", "home_team", "away_score", "home_score"}
)


def evaluate_predictions(
    predictions: pl.DataFrame,
    schedule: pl.DataFrame,
) -> tuple[BacktestResult, pl.DataFrame]:
    """Compare persisted predictions with completed schedule results."""
    started_at = perf_counter()
    _validate_inputs(predictions, schedule)

    completed = schedule.filter(
        pl.col("home_score").is_not_null()
        & pl.col("away_score").is_not_null()
        & (pl.col("home_score") != pl.col("away_score"))
    ).select(
        "game_id",
        "home_score",
        "away_score",
    )

    if completed.height == 0:
        raise ValueError("Schedule contains no completed, non-tied games.")

    evaluated = (
        predictions.join(completed, on="game_id", how="inner", validate="1:1")
        .with_columns(
            (pl.col("home_score") - pl.col("away_score")).alias(
                "actual_home_margin"
            ),
            (pl.col("home_score") > pl.col("away_score"))
            .cast(pl.Float64)
            .alias("home_win"),
            pl.when(pl.col("home_score") > pl.col("away_score"))
            .then(pl.col("home_team"))
            .otherwise(pl.col("away_team"))
            .alias("actual_winner"),
        )
        .with_columns(
            (pl.col("predicted_winner") == pl.col("actual_winner")).alias(
                "winner_correct"
            ),
            (
                pl.col("expected_home_margin") - pl.col("actual_home_margin")
            ).alias("margin_error"),
        )
        .sort(["week", "game_id"])
    )

    if evaluated.height == 0:
        raise ValueError("No completed games matched the prediction dataset.")

    probabilities = evaluated["home_win_probability"].to_list()
    outcomes = evaluated["home_win"].to_list()
    predicted_margins = evaluated["expected_home_margin"].to_list()
    actual_margins = evaluated["actual_home_margin"].to_list()
    predicted_winners = evaluated["predicted_winner"].to_list()
    actual_winners = evaluated["actual_winner"].to_list()

    home_games = evaluated.filter(pl.col("predicted_winner") == pl.col("home_team"))
    away_games = evaluated.filter(pl.col("predicted_winner") == pl.col("away_team"))

    result = BacktestResult(
        season=int(evaluated["season"][0]),
        model_version=str(evaluated["model_version"][0]),
        games_available=completed.height,
        games_evaluated=evaluated.height,
        prediction_coverage=evaluated.height / completed.height,
        winner_accuracy=winner_accuracy(predicted_winners, actual_winners),
        brier_score=brier_score(probabilities, outcomes),
        log_loss=binary_log_loss(probabilities, outcomes),
        margin_mae=mean_absolute_error(predicted_margins, actual_margins),
        margin_rmse=root_mean_squared_error(predicted_margins, actual_margins),
        home_accuracy=_conditional_accuracy(home_games),
        away_accuracy=_conditional_accuracy(away_games),
        calibration=build_calibration_buckets(evaluated),
        runtime_seconds=perf_counter() - started_at,
    )
    return result, evaluated


def _conditional_accuracy(frame: pl.DataFrame) -> float:
    if frame.height == 0:
        return 0.0
    return float(frame["winner_correct"].mean())


def _validate_inputs(predictions: pl.DataFrame, schedule: pl.DataFrame) -> None:
    missing_predictions = _REQUIRED_PREDICTION_COLUMNS.difference(
        predictions.columns
    )
    if missing_predictions:
        missing_text = ", ".join(sorted(missing_predictions))
        raise ValueError(f"Predictions are missing required columns: {missing_text}")

    missing_schedule = _REQUIRED_SCHEDULE_COLUMNS.difference(schedule.columns)
    if missing_schedule:
        missing_text = ", ".join(sorted(missing_schedule))
        raise ValueError(f"Schedule is missing required columns: {missing_text}")

    if predictions.height == 0:
        raise ValueError("Predictions contain no rows.")
    if schedule.height == 0:
        raise ValueError("Schedule contains no rows.")
    if predictions.select("game_id").n_unique() != predictions.height:
        raise ValueError("Predictions contain duplicate game rows.")
