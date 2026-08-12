from __future__ import annotations

import polars as pl
import pytest

from gridiron.validation.injury_features import validate_injury_features


def valid() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],
        "home_injury_score":[1.0],"away_injury_score":[0.5],
        "injury_score_difference":[0.5],
        "home_affected_players":[1],"away_affected_players":[1],
        "home_out_players":[1],"away_out_players":[0],
        "home_injury_report_count":[1],"away_injury_report_count":[1],
        "home_injury_known":[True],"away_injury_known":[True],
        "kickoff_guard_applied":[True],
        "source_timestamp_available": [True],
    })

def test_valid_features_pass() -> None:
    validate_injury_features(valid())

def test_bad_difference_fails() -> None:
    frame = valid().with_columns(pl.lit(9.0).alias("injury_score_difference"))
    with pytest.raises(ValueError, match="difference"):
        validate_injury_features(frame)
