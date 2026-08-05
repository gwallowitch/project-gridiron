"""Win-probability functions for Prediction Engine v1."""

from __future__ import annotations

import math

from gridiron.prediction.constants import PROBABILITY_SCALE


def home_win_probability(
    rating_difference: float,
    *,
    scale: float = PROBABILITY_SCALE,
) -> float:
    """Convert a home-centered rating difference to a probability."""
    if scale <= 0:
        raise ValueError("Probability scale must be positive.")

    return 1.0 / (1.0 + math.exp(-scale * rating_difference))
