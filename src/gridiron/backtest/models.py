"""Data models for historical prediction backtesting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    """Observed results for one predicted-probability interval."""

    lower_bound: float
    upper_bound: float
    games: int
    mean_probability: float
    observed_win_rate: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Summary metrics for one historical prediction backtest."""

    season: int
    model_version: str
    games_available: int
    games_evaluated: int
    prediction_coverage: float
    winner_accuracy: float
    brier_score: float
    log_loss: float
    margin_mae: float
    margin_rmse: float
    home_accuracy: float
    away_accuracy: float
    calibration: tuple[CalibrationBucket, ...]
    runtime_seconds: float
