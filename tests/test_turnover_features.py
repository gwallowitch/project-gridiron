from __future__ import annotations

import polars as pl

from gridiron.features.turnovers import build_turnover_features


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
        "game_id": ["g1", "g1", "g1", "g1", "future"],
        "season": [2024] * 5,
        "week": [1, 1, 1, 1, 3],
        "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA"],
        "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB"],
        "interception": [1, 0, 0, 0, 10],
        "fumble_lost": [0, 1, 0, 0, 10],
    })


def test_week_one_has_no_prior_turnover_history() -> None:
    row = build_turnover_features(schedule(), pbp()).filter(pl.col("week") == 1).row(0, named=True)
    assert row["home_turnover_known"] is False
    assert row["turnover_rate_difference"] is None


def test_week_two_uses_only_prior_week() -> None:
    row = build_turnover_features(schedule(), pbp()).filter(pl.col("week") == 2).row(0, named=True)
    assert row["home_turnover_known"] is True
    assert row["away_turnover_known"] is True
    assert row["home_interceptions_thrown_pg"] == 1.0
    assert row["home_fumbles_lost_pg"] == 1.0
    assert row["away_turnovers_committed_pg"] == 0.0


def test_future_week_is_excluded() -> None:
    row = build_turnover_features(schedule(), pbp()).filter(pl.col("week") == 2).row(0, named=True)
    assert row["home_turnovers_committed_pg"] == 2.0


def test_interceptions_and_fumbles_remain_separate() -> None:
    row = build_turnover_features(schedule(), pbp()).filter(pl.col("week") == 2).row(0, named=True)
    assert row["home_interceptions_thrown_pg"] == 1.0
    assert row["home_fumbles_lost_pg"] == 1.0
