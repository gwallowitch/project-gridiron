
from pathlib import Path

import polars as pl
import pytest

from scripts.validate_explosive_suppression_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact():
    return pl.DataFrame({
        "game_id":["g1","g2"], "season":[2024,2024],
        "home_explosive_suppression_known":[True,True],
        "away_explosive_suppression_known":[True,True],
        "explosive_off_rate_difference":[0.02,-0.02],
        "explosive_suppression_advantage":[0.03,-0.03],
        "chunk_off_rate_difference":[0.04,-0.04],
        "chunk_suppression_advantage":[0.05,-0.05],
        "explosive_yards_share_difference":[0.08,-0.08],
        "home_off_scrimmage_plays":[240,260],
        "away_off_scrimmage_plays":[240,260],
        "home_def_scrimmage_plays_faced":[240,260],
        "away_def_scrimmage_plays_faced":[240,260],
        "home_explosive_suppression_history_weeks":[6,7],
        "away_explosive_suppression_history_weeks":[6,7],
    })

def test_validate_season_accepts_valid_artifact(tmp_path: Path):
    p = tmp_path / "x.parquet"
    artifact().write_parquet(p)
    r = validate_season(p, 2024)
    assert r.rows == 2
    assert r.home_known == 1.0

def test_duplicate_game_fails(tmp_path: Path):
    p = tmp_path / "x.parquet"
    artifact().with_columns(pl.lit("g1").alias("game_id")).write_parquet(p)
    with pytest.raises(ValueError, match="duplicate"):
        validate_season(p, 2024)

def result(home_known=0.95, coverage=0.95, off_plays=250.0, history=8.0):
    return SeasonValidation(
        season=2024, rows=285, home_known=home_known, away_known=0.95,
        feature_coverage={c:coverage for c in (
            "explosive_off_rate_difference","explosive_suppression_advantage","chunk_off_rate_difference","chunk_suppression_advantage","explosive_yards_share_difference")},
        feature_mean={c:0.0 for c in (
            "explosive_off_rate_difference","explosive_suppression_advantage","chunk_off_rate_difference","chunk_suppression_advantage","explosive_yards_share_difference")},
        feature_std={c:0.1 for c in (
            "explosive_off_rate_difference","explosive_suppression_advantage","chunk_off_rate_difference","chunk_suppression_advantage","explosive_yards_share_difference")},
        sample_means={
            "home_off_scrimmage_plays":off_plays,
            "away_off_scrimmage_plays":250.0,
            "home_def_scrimmage_plays_faced":250.0,
            "away_def_scrimmage_plays_faced":250.0,
            "home_explosive_suppression_history_weeks":history,
            "away_explosive_suppression_history_weeks":8.0,
        },
    )

def test_low_known_fails():
    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([result(home_known=0.80)])

def test_low_coverage_fails():
    with pytest.raises(ValueError, match="below 85%"):
        _validate_cross_season([result(coverage=0.70)])

def test_low_play_depth_fails():
    with pytest.raises(ValueError, match="offensive scrimmage"):
        _validate_cross_season([result(off_plays=100.0)])

def test_low_history_fails():
    with pytest.raises(ValueError, match="history depth"):
        _validate_cross_season([result(history=3.0)])
