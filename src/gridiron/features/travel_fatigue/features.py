"""Pregame NFL travel and geographic-fatigue features."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

import polars as pl

_REQUIRED_SCHEDULE = {"game_id", "season", "week", "home_team", "away_team"}


@dataclass(frozen=True, slots=True)
class TeamLocation:
    latitude: float
    longitude: float
    utc_offset_standard: int


_TEAM_LOCATIONS: dict[str, TeamLocation] = {
    "ARI": TeamLocation(33.5276, -112.2626, -7),
    "ATL": TeamLocation(33.7554, -84.4008, -5),
    "BAL": TeamLocation(39.2780, -76.6227, -5),
    "BUF": TeamLocation(42.7738, -78.7870, -5),
    "CAR": TeamLocation(35.2258, -80.8528, -5),
    "CHI": TeamLocation(41.8623, -87.6167, -6),
    "CIN": TeamLocation(39.0954, -84.5160, -5),
    "CLE": TeamLocation(41.5061, -81.6995, -5),
    "DAL": TeamLocation(32.7473, -97.0945, -6),
    "DEN": TeamLocation(39.7439, -105.0201, -7),
    "DET": TeamLocation(42.3400, -83.0456, -5),
    "GB": TeamLocation(44.5013, -88.0622, -6),
    "HOU": TeamLocation(29.6847, -95.4107, -6),
    "IND": TeamLocation(39.7601, -86.1639, -5),
    "JAX": TeamLocation(30.3239, -81.6373, -5),
    "KC": TeamLocation(39.0489, -94.4839, -6),
    "LA": TeamLocation(33.9535, -118.3392, -8),
    "LAC": TeamLocation(33.9535, -118.3392, -8),
    "LV": TeamLocation(36.0909, -115.1833, -8),
    "MIA": TeamLocation(25.9580, -80.2389, -5),
    "MIN": TeamLocation(44.9738, -93.2581, -6),
    "NE": TeamLocation(42.0909, -71.2643, -5),
    "NO": TeamLocation(29.9511, -90.0812, -6),
    "NYG": TeamLocation(40.8135, -74.0745, -5),
    "NYJ": TeamLocation(40.8135, -74.0745, -5),
    "PHI": TeamLocation(39.9008, -75.1675, -5),
    "PIT": TeamLocation(40.4468, -80.0158, -5),
    "SEA": TeamLocation(47.5952, -122.3316, -8),
    "SF": TeamLocation(37.4030, -121.9700, -8),
    "TB": TeamLocation(27.9759, -82.5033, -5),
    "TEN": TeamLocation(36.1665, -86.7713, -6),
    "WAS": TeamLocation(38.9078, -76.8644, -5),
}

_TEAM_ALIASES = {"OAK": "LV", "SD": "LAC", "STL": "LA", "WSH": "WAS"}


def _canonical(team: str) -> str:
    return _TEAM_ALIASES.get(team, team)


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: " + ", ".join(sorted(missing))
        )


def _location(team: str) -> TeamLocation | None:
    return _TEAM_LOCATIONS.get(_canonical(team))


def _haversine_miles(a: TeamLocation, b: TeamLocation) -> float:
    radius = 3958.7613
    lat1 = radians(a.latitude)
    lat2 = radians(b.latitude)
    dlat = lat2 - lat1
    dlon = radians(b.longitude - a.longitude)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(h))


def _travel_values(home_team: str, away_team: str) -> dict[str, object]:
    home = _location(home_team)
    away = _location(away_team)
    if home is None or away is None:
        return {
            "travel_geography_known": False,
            "away_travel_miles": None,
            "away_time_zone_shift_hours": None,
            "eastward_time_zone_shift_hours": None,
            "westward_time_zone_shift_hours": None,
            "cross_country_travel": None,
            "long_haul_travel": None,
        }

    miles = _haversine_miles(away, home)
    shift = home.utc_offset_standard - away.utc_offset_standard
    return {
        "travel_geography_known": True,
        "away_travel_miles": miles,
        "away_time_zone_shift_hours": abs(shift),
        "eastward_time_zone_shift_hours": max(shift, 0),
        "westward_time_zone_shift_hours": max(-shift, 0),
        "cross_country_travel": miles >= 1500.0,
        "long_haul_travel": miles >= 1000.0,
    }


def _rest_columns(rest_features: pl.DataFrame) -> tuple[str | None, str | None]:
    for home, away in (
        ("home_rest_days", "away_rest_days"),
        ("home_days_rest", "away_days_rest"),
        ("home_rest", "away_rest"),
    ):
        if home in rest_features.columns and away in rest_features.columns:
            return home, away
    return None, None


def build_travel_fatigue_features(
    schedule: pl.DataFrame,
    rest_features: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build one deterministic, pregame travel-fatigue row per game."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    rows = []
    for row in schedule.select(
        "game_id", "season", "week", "home_team", "away_team"
    ).iter_rows(named=True):
        rows.append(
            {
                **row,
                **_travel_values(
                    str(row["home_team"]),
                    str(row["away_team"]),
                ),
            }
        )
    features = pl.DataFrame(rows)

    if rest_features is None or "game_id" not in rest_features.columns:
        return features.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("away_rest_days"),
            pl.lit(None, dtype=pl.Boolean).alias("short_week_away"),
            pl.lit(None, dtype=pl.Float64).alias("short_week_travel_miles"),
            pl.lit(None, dtype=pl.Float64).alias("short_week_time_zone_shift"),
            pl.lit(False).alias("travel_rest_known"),
        )

    _, away_rest = _rest_columns(rest_features)
    if away_rest is None:
        return features.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("away_rest_days"),
            pl.lit(None, dtype=pl.Boolean).alias("short_week_away"),
            pl.lit(None, dtype=pl.Float64).alias("short_week_travel_miles"),
            pl.lit(None, dtype=pl.Float64).alias("short_week_time_zone_shift"),
            pl.lit(False).alias("travel_rest_known"),
        )

    return (
        features.join(
            rest_features.select(
                "game_id",
                pl.col(away_rest).cast(pl.Float64, strict=False).alias("away_rest_days"),
            ),
            on="game_id",
            how="left",
        )
        .with_columns(
            (pl.col("away_rest_days") < 7.0).alias("short_week_away"),
            pl.col("away_rest_days").is_not_null().alias("travel_rest_known"),
        )
        .with_columns(
            pl.when(pl.col("short_week_away"))
            .then(pl.col("away_travel_miles"))
            .otherwise(0.0)
            .alias("short_week_travel_miles"),
            pl.when(pl.col("short_week_away"))
            .then(pl.col("away_time_zone_shift_hours"))
            .otherwise(0.0)
            .alias("short_week_time_zone_shift"),
        )
    )
