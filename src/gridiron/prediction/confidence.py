"""Confidence classification for game predictions."""

from __future__ import annotations

from gridiron.prediction.constants import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)


def classify_confidence(
    home_probability: float,
    *,
    medium_threshold: float = MEDIUM_CONFIDENCE_THRESHOLD,
    high_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
) -> str:
    """Classify confidence from the favored team's probability."""
    if not 0.0 <= home_probability <= 1.0:
        raise ValueError("Probability must be between 0.0 and 1.0.")
    if not 0.5 <= medium_threshold <= high_threshold <= 1.0:
        raise ValueError("Confidence thresholds are invalid.")

    favorite_probability = max(home_probability, 1.0 - home_probability)
    if favorite_probability >= high_threshold:
        return "high"
    if favorite_probability >= medium_threshold:
        return "medium"
    return "low"
