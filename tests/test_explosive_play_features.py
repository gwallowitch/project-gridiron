import polars as pl

from gridiron.features.explosive_play import (
    build_explosive_play_features,
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
                "g1", "g1", "g1", "g1",
                "g2", "g2", "g2", "g2",
                "g2", "g2", "g2", "g2",
                "g3", "g3", "g3", "g3",
                "g3", "g3", "g3", "g3",
            ],
            "posteam": (
                ["A"] * 4 + ["B"] * 4
                + ["A"] * 4 + ["B"] * 4
                + ["A"] * 4 + ["B"] * 4
            ),
            "yards_gained": [
                25.0, 5.0, 12.0, 4.0,
                10.0, 2.0, 8.0, 3.0,
                30.0, 4.0, 15.0, 2.0,
                22.0, 1.0, 11.0, 5.0,
                99.0, 99.0, 99.0, 99.0,
                99.0, 99.0, 99.0, 99.0,
            ],
            "pass_attempt": [
                1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 0.0, 0.0,
                1.0, 1.0, 0.0, 0.0,
            ],
            "rush_attempt": [
                0.0, 0.0, 1.0, 1.0,
                0.0, 0.0, 1.0, 1.0,
                0.0, 0.0, 1.0, 1.0,
                0.0, 0.0, 1.0, 1.0,
                0.0, 0.0, 1.0, 1.0,
                0.0, 0.0, 1.0, 1.0,
            ],
        }
    )


def test_week1_unknown() -> None:
    out = build_explosive_play_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_explosive_play_known"] is False
    assert row["away_explosive_play_known"] is False


def test_week2_uses_week1_only() -> None:
    out = build_explosive_play_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_explosive_pass_rate"] - 0.5) < 1e-12
    assert abs(row["home_explosive_rush_rate"] - 0.5) < 1e-12
    assert abs(row["home_explosive_play_rate"] - 0.5) < 1e-12


def test_current_game_does_not_leak() -> None:
    out = build_explosive_play_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    # Weeks 1 and 2 each have 50% explosive rates for Team A.
    assert abs(row["home_explosive_play_rate"] - 0.5) < 1e-12

    # Week 3 deliberately contains 100% explosives and cannot affect itself.
    assert row["home_explosive_play_rate"] < 1.0


def test_advantages_are_constructed() -> None:
    out = build_explosive_play_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["explosive_pass_rate_advantage"] is not None
    assert row["explosive_rush_rate_advantage"] is not None
    assert row["explosive_play_rate_advantage"] is not None
