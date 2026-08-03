"""Validation for nflverse schedule data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

REQUIRED_SCHEDULE_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "game_type",
        "gameday",
        "away_team",
        "home_team",
    }
)


def validate_schedule(frame: Any) -> None:
    """Raise a clear error when a schedule frame is unusable."""
    columns = _column_names(frame)
    missing = REQUIRED_SCHEDULE_COLUMNS.difference(columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Schedule data is missing columns: {missing_text}")

    height = getattr(frame, "height", None)
    if height is None:
        try:
            height = len(frame)
        except TypeError as exc:
            raise TypeError("Schedule object does not expose a row count.") from exc
    if height == 0:
        raise ValueError("Schedule data contains no games.")


def _column_names(frame: Any) -> set[str]:
    columns: Iterable[str] | None = getattr(frame, "columns", None)
    if columns is None:
        raise TypeError("Schedule object does not expose columns.")
    return set(columns)

