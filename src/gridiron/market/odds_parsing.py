"""Parsing helpers for sportsbook American odds."""

from __future__ import annotations


def parse_american_odds(value: object) -> int:
    """Parse numeric American odds, including EVEN-style strings."""
    if isinstance(value, str):
        normalized = value.strip().upper()

        if normalized in {"EVEN", "EV", "EVS"}:
            return 100

    return int(float(value))
