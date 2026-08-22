from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.rushing import build_rushing_features


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
            "game_id": ["g1", "g1", "g2", "g2", "g1"],
            "season": [2024] * 5,
            "week": [1, 1, 2, 2, 1],
            "posteam": ["AAA", "BBB", "AAA", "BBB", "AAA"],
            "defteam": ["BBB", "AAA", "BBB", "AAA", "BBB"],
            "rush_attempt": [1, 1, 1, 1, 0],
            "qb_kneel": [0, 0, 0, 0, 0],
            "yards_gained": [12.0, 3.0, 80.0, -5.0, 50.0],
            "epa": [0.8, -0.4, 50.0, -50.0, 100.0],
            "success": [1.0, 0.0, 1.0, 0.0, 1.0],
        }
    )


def test_week_one_has_no_prior_rushing_history() -> None:
    out = build_rushing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_rushing_known"] is False
    assert row["away_rushing_known"] is False
    assert row["rush_off_epa_difference"] is None


def test_week_two_uses_only_prior_rushing_plays() -> None:
    out = build_rushing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_rushing_known"] is True
    assert row["away_rushing_known"] is True
    assert row["home_off_rush_epa_per_play"] == pytest.approx(0.8)
    assert row["away_off_rush_epa_per_play"] == pytest.approx(-0.4)
    assert row["home_off_rush_success_rate"] == pytest.approx(1.0)
    assert row["home_off_explosive_run_rate"] == pytest.approx(1.0)


def test_current_week_extremes_cannot_leak() -> None:
    out = build_rushing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_rush_epa_per_play"]) < 10
    assert abs(row["away_off_rush_epa_per_play"]) < 10


def test_non_rush_is_excluded() -> None:
    out = build_rushing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_rush_plays"] == 1


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_rushing_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
