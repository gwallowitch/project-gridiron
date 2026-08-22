from __future__ import annotations

import polars as pl

from gridiron.features.opponent_adjusted import build_opponent_adjusted_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2024] * 4,
            "week": [1, 2, 3, 4],
            "home_team": ["AAA", "CCC", "AAA", "DDD"],
            "away_team": ["BBB", "AAA", "DDD", "AAA"],
        }
    )


def pbp() -> pl.DataFrame:
    rows = []
    games = [
        ("g1", 1, "AAA", "BBB", 0.20),
        ("g1", 1, "BBB", "AAA", -0.10),
        ("g2", 2, "CCC", "AAA", 0.30),
        ("g2", 2, "AAA", "CCC", 0.05),
        ("g3", 3, "AAA", "DDD", 0.15),
        ("g3", 3, "DDD", "AAA", -0.05),
        ("g4", 4, "DDD", "AAA", 99.0),
        ("g4", 4, "AAA", "DDD", -99.0),
    ]
    for game_id, week, offense, defense, epa in games:
        for _ in range(4):
            rows.append(
                {
                    "game_id": game_id,
                    "season": 2024,
                    "week": week,
                    "posteam": offense,
                    "defteam": defense,
                    "play_type": "pass",
                    "epa": epa,
                }
            )
    return pl.DataFrame(rows)


def test_early_games_are_unknown() -> None:
    out = build_opponent_adjusted_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)
    assert row["home_opponent_adjusted_known"] is False
    assert row["opponent_adjusted_off_epa_difference"] is None


def test_history_becomes_known_after_two_prior_games() -> None:
    out = build_opponent_adjusted_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)
    assert row["home_opponent_adjusted_history_weeks"] == 2
    assert row["home_opponent_adjusted_opponents"] == 2


def test_current_week_extremes_do_not_leak() -> None:
    out = build_opponent_adjusted_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 4).row(0, named=True)
    value = row["away_opponent_adjusted_off_epa"]
    assert value is not None
    assert abs(value) < 10.0


def test_output_has_one_row_per_game() -> None:
    out = build_opponent_adjusted_features(schedule(), pbp())
    assert out.height == 4
    assert out["game_id"].n_unique() == 4
