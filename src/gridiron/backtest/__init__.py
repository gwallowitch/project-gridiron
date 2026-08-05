"""Historical backtesting tools for Project Gridiron."""

from gridiron.backtest.evaluator import evaluate_predictions as evaluate_predictions
from gridiron.backtest.models import BacktestResult as BacktestResult
from gridiron.backtest.pipeline import run_backtest_pipeline as run_backtest_pipeline

__all__ = ["BacktestResult", "evaluate_predictions", "run_backtest_pipeline"]
