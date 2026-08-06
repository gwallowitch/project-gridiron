from __future__ import annotations

import polars as pl

from gridiron.features.qb.features import build_qb_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
        }
    )


def test_builds_known_qb_difference() -> None:
    starters = pl.DataFrame(
        {
            "season": [2025, 2025],
            "week": [1, 1],
            "team": ["AAA", "BBB"],
            "qb_name": ["Home QB", "Away QB"],
        }
    )
    ratings = pl.DataFrame(
        {
            "qb_name": ["Home QB", "Away QB"],
            "rating": [5.0, 2.0],
        }
    )

    row = build_qb_features(
        schedule(),
        starters,
        ratings,
    ).row(0, named=True)

    assert row["home_qb"] == "Home QB"
    assert row["away_qb"] == "Away QB"
    assert row["qb_rating_difference"] == 3.0
    assert row["home_qb_known"] is True
    assert row["away_qb_known"] is True


def test_unknown_qbs_receive_neutral_defaults() -> None:
    starters = pl.DataFrame(
        schema={
            "season": pl.Int32,
            "week": pl.Int32,
            "team": pl.String,
            "qb_name": pl.String,
        }
    )
    ratings = pl.DataFrame(
        schema={"qb_name": pl.String, "rating": pl.Float64}
    )

    row = build_qb_features(
        schedule(),
        starters,
        ratings,
    ).row(0, named=True)

    assert row["home_qb"] == "UNKNOWN"
    assert row["away_qb"] == "UNKNOWN"
    assert row["home_qb_rating"] == 0.0
    assert row["away_qb_rating"] == 0.0
    assert row["qb_rating_difference"] == 0.0
