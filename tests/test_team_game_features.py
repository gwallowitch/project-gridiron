from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.team_game import build_team_game_features
from gridiron.validation.team_game_features import (
    validate_team_game_features,
)


def sample_play_by_play() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "play_id": [1, 2, 3, 4, 5, 6],
            "game_id": ["2025_01_A_B"] * 6,
            "season": [2025] * 6,
            "week": [1] * 6,
            "posteam": ["A", "A", "A", "B", "B", "B"],
            "defteam": ["B", "B", "B", "A", "A", "A"],
            "play_type": ["run", "pass", "punt", "run", "pass", "pass"],
            "epa": [1.0, -0.5, 2.0, 0.5, 1.5, -1.0],
            "success": [1.0, 0.0, 1.0, 1.0, 1.0, 0.0],
            "yards_gained": [12.0, 5.0, 0.0, 4.0, 25.0, 0.0],
            "pass_attempt": [0.0, 1.0, 0.0, 0.0, 1.0, 1.0],
            "rush_attempt": [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            "interception": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            "fumble_lost": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        }
    )


def test_build_team_game_features_returns_two_rows() -> None:
    result = build_team_game_features(sample_play_by_play())

    assert result.height == 2
    assert result["team"].to_list() == ["A", "B"]


def test_build_team_game_features_excludes_non_scrimmage_plays() -> None:
    result = build_team_game_features(sample_play_by_play())
    team_a = result.filter(pl.col("team") == "A").row(
        0,
        named=True,
    )

    assert team_a["offensive_plays"] == 2
    assert team_a["offensive_yards"] == 17.0
    assert team_a["offensive_epa"] == 0.5
    assert team_a["offensive_epa_per_play"] == pytest.approx(0.25)


def test_build_team_game_features_calculates_rates() -> None:
    result = build_team_game_features(sample_play_by_play())
    team_a = result.filter(pl.col("team") == "A").row(
        0,
        named=True,
    )

    assert team_a["offensive_success_rate"] == pytest.approx(0.5)
    assert team_a["explosive_play_rate"] == pytest.approx(0.5)
    assert team_a["turnovers"] == 1
    assert team_a["turnover_rate"] == pytest.approx(0.5)


def test_build_team_game_features_joins_defensive_metrics() -> None:
    result = build_team_game_features(sample_play_by_play())
    team_a = result.filter(pl.col("team") == "A").row(
        0,
        named=True,
    )

    assert team_a["defensive_epa_allowed_per_play"] == pytest.approx(
        1.0 / 3.0
    )
    assert team_a["takeaways"] == 1


def test_validate_team_game_features_accepts_valid_data() -> None:
    result = build_team_game_features(sample_play_by_play())

    validate_team_game_features(result)


def test_validate_team_game_features_rejects_duplicates() -> None:
    result = build_team_game_features(sample_play_by_play())
    duplicated = pl.concat([result, result.head(1)])

    with pytest.raises(ValueError, match="duplicate game/team"):
        validate_team_game_features(duplicated)


def test_build_team_game_features_rejects_missing_columns() -> None:
    incomplete = sample_play_by_play().drop("epa")

    with pytest.raises(ValueError, match="missing columns: epa"):
        build_team_game_features(incomplete)
