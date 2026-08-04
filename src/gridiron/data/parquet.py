"""Shared Parquet persistence utilities."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def write_parquet_atomically(
    frame: pl.DataFrame,
    output_path: Path,
) -> None:
    """Write a Parquet file atomically using a temporary file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".parquet.tmp")

    try:
        frame.write_parquet(
            temporary_path,
            compression="zstd",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
