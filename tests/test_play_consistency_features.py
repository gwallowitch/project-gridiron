import polars as pl

from gridiron.features.play_consistency import (
    build_play_consistency_features,
)


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2025, 2025, 2025],
            "week": [1, 2, 3],
            "home_team": ["A", "A", "A"],
            "away_team": ["B", "B", "B"],
        }
    )


def pbp() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [
                "g1", "g1", "g1", "g1",
                "g2", "g2", "g2", "g2",
                "g3", "g3", "g3", "g3",
            ],
            "posteam": ["A", "A", "B", "B"] * 3,
            "defteam": ["B", "B", "A", "A"] * 3,
            "yards_gained": [
                5.0, -2.0, 3.0, -1.0,
                6.0, -3.0, 2.0, -2.0,
                99.0, 99.0, -99.0, -99.0,
            ],
            "epa": [
                0.5, -0.4, 0.2, -0.3,
                0.6, -0.5, 0.1, -0.2,
                99.0, 99.0, -99.0, -99.0,
            ],
            "pass_attempt": [1.0, 0.0, 1.0, 0.0] * 3,
            "rush_attempt": [0.0, 1.0, 0.0, 1.0] * 3,
        }
    )


def test_week1_unknown() -> None:
    out = build_play_consistency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_play_consistency_known"] is False
    assert row["away_play_consistency_known"] is False


def test_week2_uses_week1_only() -> None:
    out = build_play_consistency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_success_rate"] - 0.5) < 1e-12
    assert abs(row["home_off_negative_play_rate"] - 0.5) < 1e-12


def test_current_game_does_not_leak() -> None:
    out = build_play_consistency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    assert abs(row["home_off_success_rate"] - 0.5) < 1e-12
    assert row["home_off_success_rate"] < 1.0


def test_matchup_advantages_are_constructed() -> None:
    out = build_play_consistency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["off_success_rate_advantage"] is not None
    assert row["def_success_prevention_advantage"] is not None
    assert row["success_rate_matchup_advantage"] is not None
    assert row["negative_play_matchup_advantage"] is not None
