from __future__ import annotations

import polars as pl

from gridiron.features.injuries import (
    build_game_injury_features,
    normalize_injury_reports,
)
from gridiron.validation.injury_features import (
    validate_injury_features,
)


def raw_2025_without_timestamp() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025],
            "season_type": ["REG"],
            "game_type": ["REG"],
            "team": ["AAA"],
            "week": [1],
            "gsis_id": ["p1"],
            "position": ["WR"],
            "full_name": ["Player One"],
            "first_name": ["Player"],
            "last_name": ["One"],
            "report_primary_injury": ["Ankle"],
            "report_secondary_injury": [None],
            "report_status": ["Out"],
            "practice_primary_injury": ["Ankle"],
            "practice_secondary_injury": [None],
            "practice_status": [
                "Did Not Participate In Practice"
            ],
        }
    )


def test_2025_schema_without_timestamp_normalizes() -> None:
    frame = normalize_injury_reports(
        raw_2025_without_timestamp()
    )

    assert frame["source_timestamp_known"].item() is False
    assert frame["source_modified_at"].null_count() == 1


def test_timestamp_unknown_data_is_neutral_at_game_level() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
        }
    )
    injuries = normalize_injury_reports(
        raw_2025_without_timestamp()
    )

    features = build_game_injury_features(
        schedule,
        injuries,
    )
    row = features.row(0, named=True)

    assert row["home_injury_score"] == 0.0
    assert row["away_injury_score"] == 0.0
    assert row["home_injury_known"] is False
    assert row["away_injury_known"] is False
    assert row["source_timestamp_available"] is False

    validate_injury_features(features)
