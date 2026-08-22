from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.explosive_suppression import (
    build_explosive_suppression_features,
)


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "week": [1, 2],
            "home_team": ["AAA", "AAA"],
            "away_team": ["BBB", "BBB"],
        }
    )


def pbp() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"] * 6 + ["g2", "g2"],
            "season": [2024] * 8,
            "week": [1] * 6 + [2, 2],
            "posteam": [
                "AAA", "AAA", "AAA",
                "BBB", "BBB", "BBB",
                "AAA", "BBB",
            ],
            "defteam": [
                "BBB", "BBB", "BBB",
                "AAA", "AAA", "AAA",
                "BBB", "AAA",
            ],
            "play_type": [
                "run", "pass", "pass",
                "run", "pass", "pass",
                "run", "pass",
            ],
            "yards_gained": [
                5.0, 12.0, 25.0,
                3.0, 8.0, 21.0,
                99.0, 99.0,
            ],
        }
    )


def test_week_one_has_no_prior_history() -> None:
    out = build_explosive_suppression_features(
        schedule(),
        pbp(),
    )
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_explosive_suppression_known"] is False
    assert row["away_explosive_suppression_known"] is False
    assert row["explosive_off_rate_difference"] is None


def test_week_two_uses_only_week_one_history() -> None:
    out = build_explosive_suppression_features(
        schedule(),
        pbp(),
    )
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_explosive_suppression_known"] is True
    assert row["away_explosive_suppression_known"] is True

    assert row["home_off_explosive_play_rate"] == pytest.approx(1 / 3)
    assert row["away_off_explosive_play_rate"] == pytest.approx(1 / 3)

    assert row["home_off_chunk_play_rate"] == pytest.approx(2 / 3)
    assert row["away_off_chunk_play_rate"] == pytest.approx(1 / 3)


def test_current_week_extremes_do_not_leak() -> None:
    out = build_explosive_suppression_features(
        schedule(),
        pbp(),
    )
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_explosive_play_rate"] < 1.0
    assert row["away_off_explosive_play_rate"] < 1.0


def test_defensive_suppression_direction_is_home_positive() -> None:
    out = build_explosive_suppression_features(
        schedule(),
        pbp(),
    )
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    expected = (
        row["away_def_explosive_play_rate_allowed"]
        - row["home_def_explosive_play_rate_allowed"]
    )
    assert row["explosive_suppression_advantage"] == pytest.approx(expected)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(
        ValueError,
        match="missing required columns",
    ):
        build_explosive_suppression_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
