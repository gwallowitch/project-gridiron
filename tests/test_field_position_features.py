from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.field_position import build_field_position_features


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
            "game_id": ["g1", "g1", "g1", "g1", "g2", "g2"],
            "season": [2024] * 6,
            "week": [1, 1, 1, 1, 2, 2],
            "drive": [1, 1, 2, 2, 1, 2],
            "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA", "BBB"],
            "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB", "AAA"],
            "play_type": ["run", "pass", "pass", "run", "run", "pass"],
            "yardline_100": [75.0, 60.0, 55.0, 40.0, 5.0, 95.0],
        }
    )


def test_week_one_has_no_prior_field_position_history() -> None:
    out = build_field_position_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_field_position_known"] is False
    assert row["away_field_position_known"] is False
    assert row["off_start_field_position_advantage"] is None


def test_week_two_uses_only_prior_drive_starts() -> None:
    out = build_field_position_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_field_position_known"] is True
    assert row["away_field_position_known"] is True
    assert row["home_off_avg_start_yardline_100"] == pytest.approx(75.0)
    assert row["away_off_avg_start_yardline_100"] == pytest.approx(55.0)


def test_only_first_play_of_drive_sets_start_position() -> None:
    out = build_field_position_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_drives_started"] == 1
    assert row["away_off_drives_started"] == 1


def test_current_week_extremes_do_not_leak() -> None:
    out = build_field_position_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_avg_start_yardline_100"] != 5.0
    assert row["away_off_avg_start_yardline_100"] != 95.0


def test_hidden_yards_is_sum_of_offense_and_defense_advantages() -> None:
    out = build_field_position_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    expected = (
        row["off_start_field_position_advantage"]
        + row["def_field_position_advantage"]
    )
    assert row["hidden_yards_field_position_advantage"] == pytest.approx(expected)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_field_position_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
