from __future__ import annotations

import polars as pl

from gridiron.features.qb.history import normalize_weekly_qb_stats


def raw_frame() -> pl.DataFrame:
    return pl.DataFrame({
        "season":[2025],"week":[1],"team":["AAA"],"player_id":["p1"],
        "player_display_name":["QB One"],"position":["QB"],"attempts":[30],
        "completions":[20],"passing_yards":[250],"passing_tds":[2],
        "passing_interceptions":[1],
    })

def test_nflreadpy_schema_maps_passing_interceptions() -> None:
    row = normalize_weekly_qb_stats(raw_frame()).row(0, named=True)
    assert row["interceptions"] == 1.0

def test_normalization_is_idempotent() -> None:
    once = normalize_weekly_qb_stats(raw_frame())
    twice = normalize_weekly_qb_stats(once)
    assert once.equals(twice)
