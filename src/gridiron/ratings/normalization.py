"""Metric normalization utilities for Project Gridiron."""

from __future__ import annotations

import polars as pl

LEAGUE_AVERAGE = 100.0
POINTS_PER_STD = 10.0


def normalize_metric(
    frame: pl.DataFrame,
    column: str,
    *,
    higher_is_better: bool = True,
) -> pl.Series:
    """Normalize a single metric to a 100-centered rating."""

    values = frame[column]
    mean = values.mean()
    std = values.std()

    if std is None or std == 0:
        return pl.Series(
            name=f"{column}_rating",
            values=[LEAGUE_AVERAGE] * frame.height,
        )

    z = (values - mean) / std

    if not higher_is_better:
        z = -z

    return pl.Series(
        name=f"{column}_rating",
        values=LEAGUE_AVERAGE + POINTS_PER_STD * z,
    )


def normalize_metrics(
    frame: pl.DataFrame,
    metrics: dict[str, bool],
) -> pl.DataFrame:
    """Normalize multiple metrics."""

    result = frame.clone()

    for column, higher_is_better in metrics.items():
        result = result.with_columns(
            normalize_metric(
                result,
                column,
                higher_is_better=higher_is_better,
            )
        )

    return result