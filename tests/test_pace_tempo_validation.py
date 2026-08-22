import polars as pl
import pytest

from gridiron.validation.pace_tempo_features import validate_pace_tempo_features


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [2],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_pregame_offensive_plays": [62.0],
            "away_pregame_offensive_plays": [58.0],
            "home_pregame_seconds_to_snap": [24.0],
            "away_pregame_seconds_to_snap": [27.0],
            "home_pregame_tempo_index": [2.5],
            "away_pregame_tempo_index": [2.2],
            "home_pace_tempo_known": [True],
            "away_pace_tempo_known": [True],
            "pace_play_volume_advantage": [4.0],
            "pace_seconds_advantage": [3.0],
            "tempo_index_advantage": [0.3],
        }
    )


def test_validation_accepts_good_frame() -> None:
    validate_pace_tempo_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_pace_tempo_features(pl.concat([valid(), valid()]))
