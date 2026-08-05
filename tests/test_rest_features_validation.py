from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from gridiron.validation.rest_features import validate_rest_features


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "gameday": [date(2025, 9, 4)],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_rest_days": [7],
            "away_rest_days": [7],
            "rest_advantage": [0],
        }
    )


def test_valid_frame_passes() -> None:
    validate_rest_features(valid_frame())


def test_duplicate_games_are_rejected() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])
    with pytest.raises(ValueError, match="duplicate"):
        validate_rest_features(frame)


def test_incorrect_advantage_is_rejected() -> None:
    frame = valid_frame().with_columns(
        pl.lit(2).alias("rest_advantage")
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_rest_features(frame)
