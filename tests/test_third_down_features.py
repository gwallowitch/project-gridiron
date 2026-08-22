from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.third_down import build_third_down_features


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
            "game_id": [
                "g1",
                "g1",
                "g1",
                "g1",
                "g2",
                "g2",
            ],
            "season": [2024] * 6,
            "week": [1, 1, 1, 1, 2, 2],
            "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA", "BBB"],
            "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB", "AAA"],
            "down": [3, 3, 3, 3, 3, 3],
            "ydstogo": [5.0, 8.0, 4.0, 10.0, 2.0, 2.0],
            "yards_gained": [6.0, 2.0, 2.0, 12.0, 99.0, -99.0],
            "play_type": ["run", "pass", "pass", "run", "run", "pass"],
            "epa": [0.5, -0.4, -0.2, 0.7, 99.0, -99.0],
        }
    )


def test_week_one_has_no_prior_third_down_history() -> None:
    out = build_third_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_third_down_known"] is False
    assert row["away_third_down_known"] is False
    assert row["third_down_off_epa_difference"] is None


def test_week_two_uses_only_prior_third_down_plays() -> None:
    out = build_third_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_third_down_known"] is True
    assert row["away_third_down_known"] is True
    assert row["home_off_third_down_conversion_rate"] == pytest.approx(0.5)
    assert row["away_off_third_down_conversion_rate"] == pytest.approx(0.5)
    assert row["home_off_third_and_long_conversion_rate"] == pytest.approx(0.0)
    assert row["away_off_third_and_long_conversion_rate"] == pytest.approx(1.0)


def test_current_week_extremes_do_not_leak() -> None:
    out = build_third_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_third_down_epa"]) < 10
    assert abs(row["away_off_third_down_epa"]) < 10


def test_home_centered_defensive_difference_is_oriented_correctly() -> None:
    out = build_third_down_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["third_down_stop_difference"] == pytest.approx(0.0)
    assert row["third_and_long_conversion_difference"] < 0


def test_non_third_down_plays_are_excluded() -> None:
    extra = pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [1],
            "posteam": ["AAA"],
            "defteam": ["BBB"],
            "down": [2],
            "ydstogo": [1.0],
            "yards_gained": [99.0],
            "play_type": ["run"],
            "epa": [99.0],
        }
    )
    out = build_third_down_features(schedule(), pl.concat([pbp(), extra]))
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_third_down_epa"]) < 10


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_third_down_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
