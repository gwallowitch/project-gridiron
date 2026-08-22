import polars as pl

from gridiron.features.pace_tempo import build_pace_tempo_features


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
            "game_id": ["g1"] * 4 + ["g2"] * 4 + ["g3"] * 4,
            "posteam": ["A", "A", "B", "B"] * 3,
            "play_type": ["run", "pass", "run", "pass"] * 3,
            "play_clock": [
                20, 22, 28, 30,
                18, 20, 27, 29,
                10, 10, 10, 10,
            ],
        }
    )


def test_current_week_does_not_leak() -> None:
    out = build_pace_tempo_features(schedule(), pbp())
    week3 = out.filter(pl.col("week") == 3).row(0, named=True)

    # Week 3 must use Weeks 1-2 only. The deliberately extreme Week 3 values
    # must not affect its own pregame features.
    assert week3["home_pregame_seconds_to_snap"] == 20.0
    assert week3["away_pregame_seconds_to_snap"] == 28.5


def test_week1_is_unknown() -> None:
    out = build_pace_tempo_features(schedule(), pbp())
    week1 = out.filter(pl.col("week") == 1).row(0, named=True)

    assert week1["home_pace_tempo_known"] is False
    assert week1["away_pace_tempo_known"] is False


def test_week2_has_prior_history() -> None:
    out = build_pace_tempo_features(schedule(), pbp())
    week2 = out.filter(pl.col("week") == 2).row(0, named=True)

    assert week2["home_pace_tempo_known"] is True
    assert week2["away_pace_tempo_known"] is True
