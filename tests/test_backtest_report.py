from __future__ import annotations

from gridiron.backtest.models import BacktestResult, CalibrationBucket
from gridiron.backtest.report import format_backtest_report


def test_report_contains_core_metrics() -> None:
    result = BacktestResult(
        season=2025,
        model_version="prediction_v1",
        games_available=2,
        games_evaluated=2,
        prediction_coverage=1.0,
        winner_accuracy=0.5,
        brier_score=0.22,
        log_loss=0.65,
        margin_mae=7.0,
        margin_rmse=9.0,
        home_accuracy=0.5,
        away_accuracy=0.5,
        calibration=(CalibrationBucket(0.5, 0.6, 2, 0.55, 0.5),),
        runtime_seconds=0.1,
    )
    report = format_backtest_report(result)
    assert "PROJECT GRIDIRON BACKTEST" in report
    assert "Winner accuracy" in report
    assert "Brier score" in report
    assert "predicted=55.0%" in report
