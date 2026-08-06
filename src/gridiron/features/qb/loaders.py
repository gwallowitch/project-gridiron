"""CSV loaders for quarterback ratings and starter assignments."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.features.qb.models import (
    RATING_COLUMNS,
    STARTER_COLUMNS,
)


def load_qb_ratings(path: Path) -> pl.DataFrame:
    """Load and validate quarterback ratings from CSV."""
    if not path.exists():
        return pl.DataFrame(
            schema={"qb_name": pl.String, "rating": pl.Float64}
        )

    frame = pl.read_csv(path)
    missing = RATING_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"QB ratings file is missing columns: {missing_text}"
        )

    frame = frame.select(
        pl.col("qb_name").cast(pl.String).str.strip_chars(),
        pl.col("rating").cast(pl.Float64),
    )

    if frame.filter(pl.col("qb_name") == "").height:
        raise ValueError("QB ratings contain blank names.")
    if frame["qb_name"].n_unique() != frame.height:
        raise ValueError("QB ratings contain duplicate quarterbacks.")
    if frame["rating"].null_count():
        raise ValueError("QB ratings contain null values.")

    return frame.sort("qb_name")


def load_qb_starters(path: Path) -> pl.DataFrame:
    """Load and validate weekly quarterback starters from CSV."""
    if not path.exists():
        return pl.DataFrame(
            schema={
                "season": pl.Int32,
                "week": pl.Int32,
                "team": pl.String,
                "qb_name": pl.String,
            }
        )

    frame = pl.read_csv(path)
    missing = STARTER_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"QB starters file is missing columns: {missing_text}"
        )

    frame = frame.select(
        pl.col("season").cast(pl.Int32),
        pl.col("week").cast(pl.Int32),
        pl.col("team").cast(pl.String).str.strip_chars(),
        pl.col("qb_name").cast(pl.String).str.strip_chars(),
    )

    if frame.filter(
        (pl.col("team") == "") | (pl.col("qb_name") == "")
    ).height:
        raise ValueError("QB starters contain blank team or QB names.")

    duplicate_count = (
        frame.group_by(["season", "week", "team"])
        .len()
        .filter(pl.col("len") > 1)
        .height
    )
    if duplicate_count:
        raise ValueError(
            "QB starters contain duplicate season/week/team rows."
        )

    return frame.sort(["season", "week", "team"])
