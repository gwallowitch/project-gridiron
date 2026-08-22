from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.special_teams import build_special_teams_features


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
            "posteam": ["AAA", "BBB", "AAA", "BBB", "AAA", "BBB"],
            "defteam": ["BBB", "AAA", "BBB", "AAA", "BBB", "AAA"],
            "play_type": ["field_goal", "field_goal", "punt", "punt", "field_goal", "punt"],
            "field_goal_result": ["made", "missed", None, None, "made", None],
            "kick_distance": [45.0, 52.0, None, None, 60.0, None],
            "punt_attempt": [0, 0, 1, 1, 0, 1],
            "punter_player_name": [None, None, "P1", "P2", None, "P2"],
            "return_yards": [None, None, 5.0, 12.0, None, 99.0],
            "touchback": [0, 0, 0, 1, 0, 0],
        }
    )


def test_week_one_has_no_prior_special_teams_history() -> None:
    out = build_special_teams_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_special_teams_known"] is False
    assert row["away_special_teams_known"] is False
    assert row["fg_make_rate_difference"] is None


def test_week_two_uses_only_prior_special_teams_plays() -> None:
    out = build_special_teams_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_special_teams_known"] is True
    assert row["away_special_teams_known"] is True
    assert row["home_fg_make_rate"] == pytest.approx(1.0)
    assert row["away_fg_make_rate"] == pytest.approx(0.0)


def test_current_week_extremes_do_not_leak() -> None:
    out = build_special_teams_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_punt_return_yards_gained"] == pytest.approx(12.0)
    assert row["away_punt_return_yards_gained"] == pytest.approx(5.0)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_special_teams_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
