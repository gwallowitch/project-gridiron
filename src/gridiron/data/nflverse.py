"""Thin, replaceable gateway around nflreadpy.

Keeping third-party calls in this module prevents nflreadpy-specific details
from spreading through the rest of the application.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class NFLVerseGateway:
    """Load NFL datasets through the maintained nflreadpy package."""

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            try:
                import nflreadpy as client
            except ImportError as exc:
                raise RuntimeError(
                    "nflreadpy is not installed. Run: python -m pip install -e ."
                ) from exc
        self._client = client

    def schedules(self, seasons: Sequence[int]) -> Any:
        """Return schedules for one or more seasons."""
        normalized = _normalize_seasons(seasons)
        return self._client.load_schedules(normalized)

    def play_by_play(self, seasons: Sequence[int]) -> Any:
        """Return play-by-play records for one or more seasons."""
        normalized = _normalize_seasons(seasons)
        return self._client.load_pbp(normalized)


def _normalize_seasons(seasons: Sequence[int]) -> list[int]:
    normalized = sorted(set(seasons))
    if not normalized:
        raise ValueError("At least one season is required.")
    if any(season < 1999 or season > 2100 for season in normalized):
        raise ValueError("NFL seasons must be between 1999 and 2100.")
    return normalized

