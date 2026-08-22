from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.fourth_down import build_fourth_down_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id": ["g1", "g2"],
        "season": [2024, 2024],
        "week": [1, 2],
        "home_team": ["AAA", "AAA"],
        "away_team": ["BBB", "BBB"],
    })


def pbp() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id": ["g1", "g1", "g1", "g1", "g2", "g2"],
        "season": [2024] * 6,
        "week": [1, 1, 1, 1, 2, 2],
        "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA", "BBB"],
        "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB", "AAA"],
        "down": [4, 4, 4, 4, 4, 4],
        "ydstogo": [1.0, 5.0, 2.0, 6.0, 1.0, 1.0],
        "yards_gained": [2.0, 1.0, 1.0, 8.0, 99.0, -99.0],
        "play_type": ["run", "pass", "run", "pass", "run", "pass"],
        "epa": [0.8, -0.7, -0.4, 1.0, 99.0, -99.0],
    })


def test_week_one_has_no_prior_fourth_down_history() -> None:
    out = build_fourth_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)
    assert row["home_fourth_down_known"] is False
    assert row["away_fourth_down_known"] is False
    assert row["fourth_down_off_epa_difference"] is None


def test_week_two_uses_only_prior_fourth_down_plays() -> None:
    out = build_fourth_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)
    assert row["home_fourth_down_known"] is True
    assert row["away_fourth_down_known"] is True
    assert row["home_off_fourth_down_conversion_rate"] == pytest.approx(0.5)
    assert row["away_off_fourth_down_conversion_rate"] == pytest.approx(0.5)
    assert row["home_off_fourth_short_conversion_rate"] == pytest.approx(1.0)
    assert row["away_off_fourth_short_conversion_rate"] == pytest.approx(0.0)


def test_current_week_extremes_do_not_leak() -> None:
    out = build_fourth_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)
    assert abs(row["home_off_fourth_down_epa"]) < 10
    assert abs(row["away_off_fourth_down_epa"]) < 10


def test_non_fourth_down_plays_are_excluded() -> None:
    extra = pl.DataFrame({
        "game_id": ["g1"], "season": [2024], "week": [1],
        "posteam": ["AAA"], "defteam": ["BBB"], "down": [3],
        "ydstogo": [1.0], "yards_gained": [99.0],
        "play_type": ["run"], "epa": [99.0],
    })
    out = build_fourth_down_features(schedule(), pl.concat([pbp(), extra]))
    row = out.filter(pl.col("week") == 2).row(0, named=True)
    assert abs(row["home_off_fourth_down_epa"]) < 10


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_fourth_down_features(schedule(), pl.DataFrame({"season": [2024]}))
