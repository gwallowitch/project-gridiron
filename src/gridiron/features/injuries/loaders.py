"""Normalization for nflverse injury-report data."""

from __future__ import annotations

import polars as pl

from gridiron.features.injuries.models import (
    BASE_RAW_INJURY_COLUMNS,
    PRACTICE_SEVERITY,
    REPORT_SEVERITY,
)


def normalize_injury_reports(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize verified nflverse injury fields into a stable schema.

    nflverse 2022-2024 exposes ``date_modified`` while the verified 2025
    dataset does not. Missing source timestamps are preserved as null and
    marked unknown; downstream feature construction excludes them from injury
    scoring so they cannot silently introduce future-data leakage.
    """
    missing = BASE_RAW_INJURY_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(
            "Injury data is missing columns: "
            + ", ".join(sorted(missing))
        )

    timestamp_expr = (
        pl.col("date_modified")
        .cast(pl.Datetime(time_unit="us", time_zone="UTC"))
        if "date_modified" in frame.columns
        else pl.lit(
            None,
            dtype=pl.Datetime(time_unit="us", time_zone="UTC"),
        )
    )

    result = (
        frame.select(
            pl.col("season").cast(pl.Int32),
            pl.col("game_type").cast(pl.String),
            pl.col("team").cast(pl.String),
            pl.col("week").cast(pl.Int32),
            pl.col("gsis_id").cast(pl.String),
            pl.col("position").cast(pl.String),
            pl.col("full_name").cast(pl.String),
            pl.col("report_primary_injury").cast(pl.String),
            pl.col("report_secondary_injury").cast(pl.String),
            pl.col("report_status").cast(pl.String),
            pl.col("practice_primary_injury").cast(pl.String),
            pl.col("practice_secondary_injury").cast(pl.String),
            pl.col("practice_status").cast(pl.String),
            timestamp_expr.alias("source_modified_at"),
        )
        .filter(pl.col("game_type") == "REG")
        .with_columns(
            _mapping_expr(
                REPORT_SEVERITY,
                "report_status",
            ).alias("report_severity"),
            _mapping_expr(
                PRACTICE_SEVERITY,
                "practice_status",
            ).alias("practice_severity"),
        )
        .with_columns(
            pl.max_horizontal(
                "report_severity",
                "practice_severity",
            ).alias("player_injury_severity"),
            (
                pl.col("report_status").is_not_null()
                | pl.col("practice_status").is_not_null()
            ).alias("has_injury_report"),
            pl.col("source_modified_at")
            .is_not_null()
            .alias("source_timestamp_known"),
        )
        .sort(
            [
                "season",
                "week",
                "team",
                "gsis_id",
                "source_modified_at",
            ]
        )
    )

    if result.filter(
        pl.col("team").is_null()
        | pl.col("gsis_id").is_null()
    ).height:
        raise ValueError(
            "Injury data contains missing team or player identity."
        )

    return result


def _mapping_expr(
    mapping: dict[str, float],
    column: str,
) -> pl.Expr:
    expr = pl.lit(0.0)
    for value, severity in mapping.items():
        expr = (
            pl.when(pl.col(column) == value)
            .then(pl.lit(severity))
            .otherwise(expr)
        )
    return expr
