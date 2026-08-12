"""Data models for Project Gridiron experiments."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    name: str
    home_field_advantage: float
    probability_scale: float
    margin_scale: float = 1.0
    margin_intercept: float = 0.0
    rest_weight: float = 0.0
    qb_weight: float = 0.0
    injury_weight: float = 0.0

@dataclass(frozen=True, slots=True)
class ExperimentResult:
    name: str
    season: int
    home_field_advantage: float
    probability_scale: float
    margin_scale: float
    margin_intercept: float
    rest_weight: float
    qb_weight: float
    injury_weight: float
    games_evaluated: int
    winner_accuracy: float
    brier_score: float
    log_loss: float
    margin_mae: float
    margin_rmse: float
    selection_score: float
    generated_at: str

    @classmethod
    def create(cls, *, config: ExperimentConfig, season: int,
               games_evaluated: int, winner_accuracy: float,
               brier_score: float, log_loss: float, margin_mae: float,
               margin_rmse: float, selection_score: float) -> ExperimentResult:
        return cls(
            name=config.name, season=season,
            home_field_advantage=config.home_field_advantage,
            probability_scale=config.probability_scale,
            margin_scale=config.margin_scale,
            margin_intercept=config.margin_intercept,
            rest_weight=config.rest_weight,
            qb_weight=config.qb_weight,
            injury_weight=config.injury_weight,
            games_evaluated=games_evaluated,
            winner_accuracy=winner_accuracy,
            brier_score=brier_score,
            log_loss=log_loss,
            margin_mae=margin_mae,
            margin_rmse=margin_rmse,
            selection_score=selection_score,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
