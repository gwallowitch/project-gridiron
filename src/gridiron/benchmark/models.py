"""Data models for Project Gridiron benchmarks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Summary statistics describing one PGR dataset."""

    season: int
    model_version: str
    team_count: int
    week_count: int
    row_count: int
    league_average: float
    median_rating: float
    standard_deviation: float
    minimum_rating: float
    maximum_rating: float
    rating_spread: float
    average_weekly_movement: float
    maximum_weekly_movement: float
    movement_observations: int
    runtime_seconds: float
