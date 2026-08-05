from __future__ import annotations

import polars as pl
import pytest

from gridiron.prediction.engine import build_predictions


def schedule() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id": ["g1", "g2"],
        "season": [2025, 2025],
        "week": [1, 2],
        "away_team": ["A", "A"],
        "home_team": ["B", "B"],
    })


def pgr() -> pl.DataFrame:
    return pl.DataFrame({
        "season": [2025, 2025],
        "week": [1, 1],
        "team": ["A", "B"],
        "pgr_rating": [105.0, 100.0],
    })


def test_week_one_uses_neutral_prior_ratings() -> None:
    result = build_predictions(schedule(), pgr())
    row = result.filter(pl.col("week") == 1).row(0, named=True)
    assert row["home_pgr"] == 100.0
    assert row["away_pgr"] == 100.0
    assert row["expected_home_margin"] == pytest.approx(1.125)


def test_week_two_uses_week_one_pgr() -> None:
    result = build_predictions(schedule(), pgr())
    row = result.filter(pl.col("week") == 2).row(0, named=True)
    assert row["away_pgr"] == 105.0
    assert row["home_pgr"] == 100.0
    assert row["rating_difference"] == pytest.approx(-3.5)
    assert row["predicted_winner"] == "A"


def test_probabilities_sum_to_one() -> None:
    result = build_predictions(schedule(), pgr())
    totals = result["home_win_probability"] + result["away_win_probability"]
    assert totals.to_list() == pytest.approx([1.0, 1.0])


def test_prediction_engine_is_deterministic() -> None:
    assert build_predictions(schedule(), pgr()).equals(
        build_predictions(schedule(), pgr())
    )


def test_prediction_engine_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="away_team"):
        build_predictions(schedule().drop("away_team"), pgr())
