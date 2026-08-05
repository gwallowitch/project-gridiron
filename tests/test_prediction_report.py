from __future__ import annotations

import polars as pl
import pytest

from gridiron.prediction.engine import build_predictions
from gridiron.prediction.report import format_prediction_report


def valid_frame() -> pl.DataFrame:
    schedule = pl.DataFrame({
        "game_id": ["g1"], "season": [2025], "week": [1],
        "away_team": ["A"], "home_team": ["B"],
    })
    pgr = pl.DataFrame({
        "season": [2025, 2025], "week": [1, 1],
        "team": ["A", "B"], "pgr_rating": [100.0, 100.0],
    })
    return build_predictions(schedule, pgr)


def test_prediction_report_contains_matchup_and_pick() -> None:
    report = format_prediction_report(valid_frame(), week=1)
    assert "A @ B" in report
    assert "Pick:" in report
    assert "Confidence:" in report


def test_prediction_report_rejects_missing_week() -> None:
    with pytest.raises(ValueError, match="No predictions"):
        format_prediction_report(valid_frame(), week=2)
