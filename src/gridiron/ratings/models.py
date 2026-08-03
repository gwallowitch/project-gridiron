"""Shared rating-engine data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeamRating:
    """One team's calculated rating components."""

    team: str
    offense: float
    defense: float
    discipline: float
    situational: float
    overall: float
