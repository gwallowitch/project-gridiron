import polars as pl

from gridiron.features.performance_stability import (
    build_performance_stability_features,
)


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2025, 2025, 2025],
            "week": [1, 2, 3],
            "home_team": ["A", "A", "A"],
            "away_team": ["B", "B", "B"],
            "home_score": [20, 30, 99],
            "away_score": [10, 20, 0],
        }
    )


def test_week1_is_unknown() -> None:
    out = build_performance_stability_features(schedule())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_performance_stability_known"] is False
    assert row["away_performance_stability_known"] is False


def test_current_week_score_does_not_leak() -> None:
    out = build_performance_stability_features(schedule())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    # Team A prior point differentials are +10 and +10.
    # The deliberately extreme Week 3 +99 result must not affect Week 3 input.
    assert row["home_mean_point_differential"] == 10.0

    # Team B prior differentials are -10 and -10.
    assert row["away_mean_point_differential"] == -10.0

    assert row["recent_margin_advantage"] == 20.0


def test_std_uses_prior_games_only() -> None:
    frame = pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2025, 2025, 2025],
            "week": [1, 2, 3],
            "home_team": ["A", "A", "A"],
            "away_team": ["B", "B", "B"],
            "home_score": [20, 31, 100],
            "away_score": [10, 20, 0],
        }
    )

    out = build_performance_stability_features(frame)
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    assert row["home_point_differential_std"] is not None
    assert row["home_point_differential_std"] < 1.0
