"""Data models for Project Gridiron predictions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GamePrediction:
    """One explainable game prediction."""

    season: int
    week: int
    game_id: str
    away_team: str
    home_team: str
    rating_week: int
    away_pgr: float
    home_pgr: float
    home_field_advantage: float
    rating_difference: float
    expected_home_margin: float
    home_win_probability: float
    away_win_probability: float
    predicted_winner: str
    confidence: str
    model_version: str
