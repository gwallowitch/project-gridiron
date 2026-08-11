"""Game-level QB features from leakage-safe weekly ratings."""

from __future__ import annotations

import polars as pl


def build_historical_qb_features(schedule: pl.DataFrame, weekly_ratings: pl.DataFrame) -> pl.DataFrame:
    base = schedule.select("game_id","season","week","home_team","away_team")
    home = weekly_ratings.select(
        "season","week",pl.col("team").alias("home_team"),
        pl.col("qb_name").alias("home_qb"),
        pl.col("rating").alias("home_qb_rating"),
        pl.col("prior_attempts").alias("home_qb_prior_attempts"),
        pl.col("source_week").alias("home_qb_source_week"),
    )
    away = weekly_ratings.select(
        "season","week",pl.col("team").alias("away_team"),
        pl.col("qb_name").alias("away_qb"),
        pl.col("rating").alias("away_qb_rating"),
        pl.col("prior_attempts").alias("away_qb_prior_attempts"),
        pl.col("source_week").alias("away_qb_source_week"),
    )
    return (
        base.join(home,on=["season","week","home_team"],how="left",validate="m:1")
        .join(away,on=["season","week","away_team"],how="left",validate="m:1")
        .with_columns(
            pl.col("home_qb").fill_null("UNKNOWN"),
            pl.col("away_qb").fill_null("UNKNOWN"),
            pl.col("home_qb_rating").fill_null(0.0),
            pl.col("away_qb_rating").fill_null(0.0),
            pl.col("home_qb_prior_attempts").fill_null(0.0),
            pl.col("away_qb_prior_attempts").fill_null(0.0),
            pl.col("home_qb_source_week").fill_null(0),
            pl.col("away_qb_source_week").fill_null(0),
        )
        .with_columns(
            (pl.col("home_qb_rating")-pl.col("away_qb_rating")).alias("qb_rating_difference"),
            (pl.col("home_qb")!="UNKNOWN").alias("home_qb_known"),
            (pl.col("away_qb")!="UNKNOWN").alias("away_qb_known"),
        )
        .sort(["season","week","game_id"])
    )
