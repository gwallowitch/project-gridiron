from __future__ import annotations

import polars as pl

from gridiron.features.qb.history import (
    build_leakage_safe_weekly_ratings,
    build_prior_starter_assignments,
)


def weekly() -> pl.DataFrame:
    return pl.DataFrame({
        "season":[2025,2025,2025,2025],
        "week":[1,1,2,2],
        "team":["AAA","BBB","AAA","BBB"],
        "player_id":["a","b","a","b"],
        "player_display_name":["QB A","QB B","QB A","QB B"],
        "position":["QB","QB","QB","QB"],
        "attempts":[30,30,35,35],
        "completions":[20,20,25,24],
        "passing_yards":[300,200,350,210],
        "passing_tds":[3,1,4,1],
        "interceptions":[0,2,0,1],
    })

def schedule() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id":["g1","g2","g3"],
        "season":[2025,2025,2025],
        "week":[1,2,3],
        "home_team":["AAA","BBB","AAA"],
        "away_team":["BBB","AAA","BBB"],
    })

def test_week_one_is_unknown_without_prior_game() -> None:
    starters = build_prior_starter_assignments(weekly(), schedule())
    week_one = starters.filter(pl.col("week")==1)
    assert set(week_one["qb_name"].to_list()) == {"UNKNOWN"}

def test_week_two_uses_only_week_one_starter() -> None:
    starters = build_prior_starter_assignments(weekly(), schedule())
    row = starters.filter((pl.col("week")==2)&(pl.col("team")=="AAA")).row(0,named=True)
    assert row["qb_name"] == "QB A"
    assert row["source_week"] == 1

def test_week_two_rating_ignores_week_two_performance() -> None:
    first = build_leakage_safe_weekly_ratings(weekly(), schedule())
    altered = weekly().with_columns(
        pl.when((pl.col("week")==2)&(pl.col("team")=="AAA"))
        .then(pl.lit(9999))
        .otherwise(pl.col("passing_yards"))
        .alias("passing_yards")
    )
    second = build_leakage_safe_weekly_ratings(altered, schedule())
    a = first.filter((pl.col("week")==2)&(pl.col("team")=="AAA"))["rating"].item()
    b = second.filter((pl.col("week")==2)&(pl.col("team")=="AAA"))["rating"].item()
    assert a == b

def test_week_three_can_use_weeks_one_and_two() -> None:
    ratings = build_leakage_safe_weekly_ratings(weekly(), schedule())
    row = ratings.filter((pl.col("week")==3)&(pl.col("team")=="AAA")).row(0,named=True)
    assert row["source_week"] == 2
    assert row["prior_attempts"] == 65.0
