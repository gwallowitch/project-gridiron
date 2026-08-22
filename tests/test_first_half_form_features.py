import polars as pl

from gridiron.features.first_half_form import (
    build_first_half_form_features,
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
            "qtr": [1, 2, 1, 2] * 3,
            "epa": [
                0.20, 0.40, -0.10, 0.00,
                0.30, 0.50, -0.20, 0.10,
                99.0, 99.0, -99.0, -99.0,
            ],
        }
    )


def test_week1_unknown() -> None:
    out = build_first_half_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_first_half_form_known"] is False
    assert row["away_first_half_form_known"] is False


def test_current_game_first_half_does_not_leak() -> None:
    out = build_first_half_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    # Team A prior offensive EPA/play:
    # Week 1 = 0.30, Week 2 = 0.40 -> mean 0.35.
    assert abs(row["home_first_half_off_epa"] - 0.35) < 1e-12

    # Week 3's deliberately extreme 99 EPA cannot affect its own input.
    assert row["home_first_half_off_epa"] < 1.0


def test_advantages_are_constructed() -> None:
    out = build_first_half_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["first_half_off_epa_advantage"] is not None
    assert row["first_half_def_epa_advantage"] is not None
