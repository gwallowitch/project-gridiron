"""Production-safe temperature calibration for win probabilities."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True)
class TemperatureCalibrationContract:
    """Frozen production calibration contract."""

    method: str
    slope: float
    intercept: float
    source_step: str
    source_fingerprint_sha256: str
    training_seasons: tuple[int, ...]
    population_games: int

    def validate(self) -> None:
        if self.method != "temperature":
            raise ValueError(
                f"Unsupported calibration method: {self.method}"
            )
        if not math.isfinite(self.slope) or self.slope <= 0.0:
            raise ValueError("Temperature slope must be finite and > 0.")
        if self.intercept != 0.0:
            raise ValueError(
                "Temperature calibration contract requires zero intercept."
            )
        if len(self.source_fingerprint_sha256) != 64:
            raise ValueError(
                "Calibration contract fingerprint must be SHA-256."
            )
        if not self.training_seasons:
            raise ValueError(
                "Calibration contract requires training seasons."
            )
        if self.population_games <= 0:
            raise ValueError(
                "Calibration contract requires a positive population size."
            )


def calibrate_probability(
    probability: float,
    *,
    slope: float,
) -> float:
    """Apply temperature scaling while preserving the 0.5 boundary."""
    if not math.isfinite(probability):
        raise ValueError("Probability must be finite.")
    if probability < 0.0 or probability > 1.0:
        raise ValueError("Probability must be between 0.0 and 1.0.")
    if not math.isfinite(slope) or slope <= 0.0:
        raise ValueError("Calibration slope must be finite and > 0.")

    eps = 1e-15
    p = min(max(probability, eps), 1.0 - eps)
    logit = math.log(p / (1.0 - p))
    calibrated = 1.0 / (1.0 + math.exp(-slope * logit))

    if probability == 0.0:
        return 0.0
    if probability == 1.0:
        return 1.0

    return calibrated


def apply_temperature_calibration(
    frame: pl.DataFrame,
    *,
    probability_column: str,
    output_column: str,
    slope: float,
) -> pl.DataFrame:
    """Apply temperature calibration to a Polars probability column."""
    if probability_column not in frame.columns:
        raise ValueError(
            f"Missing probability column: {probability_column}"
        )

    return frame.with_columns(
        pl.col(probability_column)
        .map_elements(
            lambda value: calibrate_probability(
                float(value),
                slope=slope,
            ),
            return_dtype=pl.Float64,
        )
        .alias(output_column)
    )


def load_temperature_contract(
    path: Path | str,
) -> TemperatureCalibrationContract:
    payload = json.loads(
        Path(path).read_text(encoding="utf-8")
    )

    contract = TemperatureCalibrationContract(
        method=str(payload["method"]),
        slope=float(payload["slope"]),
        intercept=float(payload["intercept"]),
        source_step=str(payload["source_step"]),
        source_fingerprint_sha256=str(
            payload["source_fingerprint_sha256"]
        ),
        training_seasons=tuple(
            int(value)
            for value in payload["training_seasons"]
        ),
        population_games=int(payload["population_games"]),
    )
    contract.validate()
    return contract
