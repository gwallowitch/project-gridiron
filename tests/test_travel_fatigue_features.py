import polars as pl

from gridiron.features.travel_fatigue import build_travel_fatigue_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["sea_mia", "ny_phi"],
            "season": [2025, 2025],
            "week": [4, 4],
            "home_team": ["MIA", "PHI"],
            "away_team": ["SEA", "NYG"],
        }
    )


def test_cross_country_trip_is_detected() -> None:
    row = (
        build_travel_fatigue_features(schedule())
        .filter(pl.col("game_id") == "sea_mia")
        .row(0, named=True)
    )
    assert row["travel_geography_known"] is True
    assert row["away_travel_miles"] > 2500.0
    assert row["away_time_zone_shift_hours"] == 3
    assert row["eastward_time_zone_shift_hours"] == 3
    assert row["cross_country_travel"] is True


def test_short_local_trip_is_not_long_haul() -> None:
    row = (
        build_travel_fatigue_features(schedule())
        .filter(pl.col("game_id") == "ny_phi")
        .row(0, named=True)
    )
    assert row["away_travel_miles"] < 150.0
    assert row["away_time_zone_shift_hours"] == 0
    assert row["long_haul_travel"] is False


def test_short_week_interaction_uses_away_rest() -> None:
    rest = pl.DataFrame(
        {
            "game_id": ["sea_mia", "ny_phi"],
            "home_rest_days": [7, 7],
            "away_rest_days": [6, 8],
        }
    )
    out = build_travel_fatigue_features(schedule(), rest)
    sea = out.filter(pl.col("game_id") == "sea_mia").row(0, named=True)
    ny = out.filter(pl.col("game_id") == "ny_phi").row(0, named=True)

    assert sea["travel_rest_known"] is True
    assert sea["short_week_away"] is True
    assert sea["short_week_travel_miles"] > 2500.0
    assert ny["short_week_away"] is False
    assert ny["short_week_travel_miles"] == 0.0


def test_unknown_team_is_marked_unknown() -> None:
    frame = pl.DataFrame(
        {
            "game_id": ["x"],
            "season": [2025],
            "week": [1],
            "home_team": ["MIA"],
            "away_team": ["XXX"],
        }
    )
    row = build_travel_fatigue_features(frame).row(0, named=True)
    assert row["travel_geography_known"] is False
    assert row["away_travel_miles"] is None
