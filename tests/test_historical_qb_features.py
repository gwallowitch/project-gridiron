from __future__ import annotations

import polars as pl

from gridiron.features.qb.historical_features import build_historical_qb_features


def test_builds_rating_difference() -> None:
    schedule = pl.DataFrame({
        "game_id":["g1"],"season":[2025],"week":[2],
        "home_team":["AAA"],"away_team":["BBB"],
    })
    ratings = pl.DataFrame({
        "season":[2025,2025],"week":[2,2],"team":["AAA","BBB"],
        "qb_name":["QB A","QB B"],"rating":[2.0,-1.0],
        "prior_attempts":[30.0,30.0],"source_week":[1,1],
    })
    row = build_historical_qb_features(schedule, ratings).row(0,named=True)
    assert row["qb_rating_difference"] == 3.0
    assert row["home_qb_known"] is True
    assert row["away_qb_known"] is True
