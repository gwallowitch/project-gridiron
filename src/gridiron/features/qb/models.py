"""Quarterback feature constants and schemas."""

from __future__ import annotations

DEFAULT_QB_NAME = "UNKNOWN"
DEFAULT_QB_RATING = 0.0

RATING_COLUMNS = frozenset({"qb_name", "rating"})
STARTER_COLUMNS = frozenset({"season", "week", "team", "qb_name"})
SCHEDULE_COLUMNS = frozenset(
    {"game_id", "season", "week", "home_team", "away_team"}
)
