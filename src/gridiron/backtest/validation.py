"""Validation for persisted backtest game records."""

from __future__ import annotations

import math

import polars as pl

_REQUIRED_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "predicted_winner",
        "actual_winner",
        "home_win_probability",
        "expected_home_margin",
        "actual_home_margin",
        "winner_correct",
        "margin_error",
        "model_version",
    }
)


def validate_backtest_games(frame: pl.DataFrame) -> None:
    """Validate evaluated game records before persistence."""
    missing = _REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Backtest results are missing columns: {missing_text}")
    if frame.height == 0:
        raise ValueError("Backtest results contain no rows.")
    if frame.select("game_id").n_unique() != frame.height:
        raise ValueError("Backtest results contain duplicate game rows.")
    required_frame = frame.select(sorted(_REQUIRED_COLUMNS))
    if required_frame.null_count().sum_horizontal().item() > 0:
        raise ValueError("Backtest results contain null values.")

    for column in (
        "home_win_probability",
        "expected_home_margin",
        "actual_home_margin",
        "margin_error",
    ):
        if not all(math.isfinite(value) for value in frame[column].to_list()):
            raise ValueError(f"Backtest column contains non-finite values: {column}")
