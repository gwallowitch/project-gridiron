from __future__ import annotations

import polars as pl
import pytest

from gridiron.prediction.engine import build_predictions
from gridiron.prediction.validation import validate_predictions


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


def test_validate_predictions_accepts_valid_frame() -> None:
    validate_predictions(valid_frame())


def test_validate_predictions_rejects_duplicate_games() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])
    with pytest.raises(ValueError, match="duplicate"):
        validate_predictions(frame)


def test_validate_predictions_rejects_bad_probability_total() -> None:
    frame = valid_frame().with_columns(pl.lit(0.2).alias("away_win_probability"))
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_predictions(frame)
