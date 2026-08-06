from __future__ import annotations

import polars as pl
import pytest

from gridiron.validation.qb_features import validate_qb_features


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_qb": ["Home QB"],
            "away_qb": ["Away QB"],
            "home_qb_rating": [4.0],
            "away_qb_rating": [2.0],
            "qb_rating_difference": [2.0],
            "home_qb_known": [True],
            "away_qb_known": [True],
        }
    )


def test_valid_qb_features_pass() -> None:
    validate_qb_features(valid_frame())


def test_invalid_difference_is_rejected() -> None:
    frame = valid_frame().with_columns(
        pl.lit(3.0).alias("qb_rating_difference")
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_qb_features(frame)
