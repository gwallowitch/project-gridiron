"""Validation for nflverse play-by-play data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

REQUIRED_PLAY_BY_PLAY_COLUMNS = frozenset(
    {
        "play_id",
        "game_id",
        "season",
        "week",
    }
)


def validate_play_by_play(frame: Any) -> None:
    """Raise a clear error when play-by-play data is unusable."""
    columns = _column_names(frame)
    missing = REQUIRED_PLAY_BY_PLAY_COLUMNS.difference(columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Play-by-play data is missing columns: {missing_text}"
        )

    height = getattr(frame, "height", None)
    if height is None:
        try:
            height = len(frame)
        except TypeError as exc:
            raise TypeError(
                "Play-by-play object does not expose a row count."
            ) from exc

    if height == 0:
        raise ValueError("Play-by-play data contains no plays.")


def _column_names(frame: Any) -> set[str]:
    columns: Iterable[str] | None = getattr(frame, "columns", None)

    if columns is None:
        raise TypeError(
            "Play-by-play object does not expose columns."
        )

    return set(columns)
