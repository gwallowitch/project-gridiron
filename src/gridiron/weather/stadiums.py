"""NFL home-stadium coordinate registry for weather research."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StadiumLocation:
    latitude: float
    longitude: float


STADIUMS: dict[str, StadiumLocation] = {
    "ARI": StadiumLocation(33.5276, -112.2626),
    "ATL": StadiumLocation(33.7554, -84.4008),
    "BAL": StadiumLocation(39.2780, -76.6227),
    "BUF": StadiumLocation(42.7738, -78.7870),
    "CAR": StadiumLocation(35.2258, -80.8528),
    "CHI": StadiumLocation(41.8623, -87.6167),
    "CIN": StadiumLocation(39.0954, -84.5160),
    "CLE": StadiumLocation(41.5061, -81.6995),
    "DAL": StadiumLocation(32.7473, -97.0945),
    "DEN": StadiumLocation(39.7439, -105.0201),
    "DET": StadiumLocation(42.3400, -83.0456),
    "GB": StadiumLocation(44.5013, -88.0622),
    "HOU": StadiumLocation(29.6847, -95.4107),
    "IND": StadiumLocation(39.7601, -86.1639),
    "JAX": StadiumLocation(30.3239, -81.6373),
    "KC": StadiumLocation(39.0489, -94.4839),
    "LA": StadiumLocation(33.9535, -118.3392),
    "LAC": StadiumLocation(33.9535, -118.3392),
    "LV": StadiumLocation(36.0909, -115.1833),
    "MIA": StadiumLocation(25.9580, -80.2389),
    "MIN": StadiumLocation(44.9738, -93.2581),
    "NE": StadiumLocation(42.0909, -71.2643),
    "NO": StadiumLocation(29.9511, -90.0812),
    "NYG": StadiumLocation(40.8135, -74.0745),
    "NYJ": StadiumLocation(40.8135, -74.0745),
    "PHI": StadiumLocation(39.9008, -75.1675),
    "PIT": StadiumLocation(40.4468, -80.0158),
    "SEA": StadiumLocation(47.5952, -122.3316),
    "SF": StadiumLocation(37.4030, -121.9700),
    "TB": StadiumLocation(27.9759, -82.5033),
    "TEN": StadiumLocation(36.1665, -86.7713),
    "WAS": StadiumLocation(38.9078, -76.8644),
}

ALIASES = {
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LA",
    "WSH": "WAS",
}


def stadium_for_team(team: str) -> StadiumLocation | None:
    return STADIUMS.get(ALIASES.get(team, team))
