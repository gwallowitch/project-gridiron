from __future__ import annotations

import polars as pl
import pytest

from gridiron.backtest.evaluator import evaluate_predictions


def predictions() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2025, 2025],
            "week": [1, 2],
            "away_team": ["A", "C"],
            "home_team": ["B", "D"],
            "predicted_winner": ["B", "C"],
            "expected_home_margin": [3.0, -2.0],
            "home_win_probability": [0.7, 0.4],
            "model_version": ["prediction_v1", "prediction_v1"],
        }
    )


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2025, 2025, 2025],
            "away_team": ["A", "C", "E"],
            "home_team": ["B", "D", "F"],
            "away_score": [17, 24, None],
            "home_score": [20, 21, None],
        }
    )


def test_evaluate_predictions_calculates_expected_metrics() -> None:
    result, games = evaluate_predictions(predictions(), schedule())

    assert result.games_available == 2
    assert result.games_evaluated == 2
    assert result.prediction_coverage == 1.0
    assert result.winner_accuracy == 1.0
    assert result.margin_mae == pytest.approx(0.5)
    assert games["winner_correct"].to_list() == [True, True]


def test_evaluate_predictions_rejects_missing_scores() -> None:
    incomplete = schedule().with_columns(
        pl.lit(None, dtype=pl.Int64).alias("home_score")
    )
    with pytest.raises(ValueError, match="no completed"):
        evaluate_predictions(predictions(), incomplete)


def test_evaluate_predictions_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="away_score"):
        evaluate_predictions(predictions(), schedule().drop("away_score"))
