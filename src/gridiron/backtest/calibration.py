"""Probability calibration utilities."""

from __future__ import annotations

import polars as pl

from gridiron.backtest.models import CalibrationBucket

DEFAULT_BUCKETS = (
    (0.0, 0.5),
    (0.5, 0.6),
    (0.6, 0.7),
    (0.7, 0.8),
    (0.8, 0.9),
    (0.9, 1.0000000001),
)


def build_calibration_buckets(
    evaluated_games: pl.DataFrame,
) -> tuple[CalibrationBucket, ...]:
    """Summarize home-win probabilities into fixed reliability buckets."""
    required = {"home_win_probability", "home_win"}
    missing = required.difference(evaluated_games.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Calibration data is missing columns: {missing_text}")

    buckets: list[CalibrationBucket] = []
    for lower, upper in DEFAULT_BUCKETS:
        rows = evaluated_games.filter(
            (pl.col("home_win_probability") >= lower)
            & (pl.col("home_win_probability") < upper)
        )
        if rows.height == 0:
            continue
        buckets.append(
            CalibrationBucket(
                lower_bound=lower,
                upper_bound=min(upper, 1.0),
                games=rows.height,
                mean_probability=float(rows["home_win_probability"].mean()),
                observed_win_rate=float(rows["home_win"].mean()),
            )
        )
    return tuple(buckets)
