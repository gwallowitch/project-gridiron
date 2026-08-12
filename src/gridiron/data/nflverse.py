"""Thin, replaceable gateway around nflreadpy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class NFLVerseGateway:
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
        return self._client.load_schedules(_normalize_seasons(seasons))

    def play_by_play(self, seasons: Sequence[int]) -> Any:
        return self._client.load_pbp(_normalize_seasons(seasons))

    def injuries(self, seasons: Sequence[int]) -> Any:
        return self._client.load_injuries(_normalize_seasons(seasons))

def _normalize_seasons(seasons: Sequence[int]) -> list[int]:
    normalized = sorted(set(seasons))
    if not normalized:
        raise ValueError("At least one season is required.")
    if any(season < 1999 or season > 2100 for season in normalized):
        raise ValueError("NFL seasons must be between 1999 and 2100.")
    return normalized
