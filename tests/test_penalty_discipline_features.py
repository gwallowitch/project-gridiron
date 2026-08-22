from __future__ import annotations

import polars as pl

from gridiron.features.penalty_discipline import (
    build_penalty_discipline_features,
)


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2024] * 4,
            "week": [1, 2, 3, 4],
            "home_team": ["AAA"] * 4,
            "away_team": ["BBB"] * 4,
        }
    )


def pbp() -> pl.DataFrame:
    rows = []
    for week in range(1, 5):
        rows.extend(
            [
                {
                    "game_id": f"g{week}",
                    "season": 2024,
                    "week": week,
                    "posteam": "AAA",
                    "defteam": "BBB",
                    "play_type": "pass",
                    "penalty_team": "AAA" if week <= 3 else "BBB",
                    "penalty_yards": 10.0 if week <= 3 else 99.0,
                },
                {
                    "game_id": f"g{week}",
                    "season": 2024,
                    "week": week,
                    "posteam": "BBB",
                    "defteam": "AAA",
                    "play_type": "run",
                    "penalty_team": "BBB",
                    "penalty_yards": 5.0,
                },
            ]
        )
    return pl.DataFrame(rows)


def test_week_one_has_no_history() -> None:
    out = build_penalty_discipline_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_penalty_discipline_known"] is False
    assert row["penalty_yards_discipline_advantage"] is None


def test_week_three_has_two_prior_weeks() -> None:
    out = build_penalty_discipline_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    assert row["home_discipline_history_weeks"] == 2
    assert row["away_discipline_history_weeks"] == 2
    assert row["home_penalty_discipline_known"] is True


def test_current_week_penalty_does_not_leak() -> None:
    out = build_penalty_discipline_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 4).row(0, named=True)

    assert row["home_off_penalty_yards"] == 30.0
    assert row["away_def_penalty_yards"] == 0.0


def test_one_output_row_per_game() -> None:
    out = build_penalty_discipline_features(schedule(), pbp())

    assert out.height == 4
    assert out["game_id"].n_unique() == 4

