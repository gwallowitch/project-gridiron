"""Leakage-safe rolling early-down efficiency features."""
from __future__ import annotations

import polars as pl

PBP_REQUIRED = {"game_id","season","week","posteam","defteam","down","play_type","epa","success","yards_gained"}
SCHEDULE_REQUIRED = {"game_id","season","week","home_team","away_team"}

def _require(frame: pl.DataFrame, cols: set[str], label: str) -> None:
    missing = cols.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing columns: {', '.join(sorted(missing))}")

def build_early_down_features(schedule: pl.DataFrame, pbp: pl.DataFrame) -> pl.DataFrame:
    """Use only prior weeks from the same season for each game's features."""
    _require(schedule, SCHEDULE_REQUIRED, "Schedule")
    _require(pbp, PBP_REQUIRED, "Play-by-play")
    plays = pbp.filter(
        pl.col("down").is_in([1,2])
        & pl.col("play_type").is_in(["pass","run"])
        & pl.col("posteam").is_not_null()
        & pl.col("defteam").is_not_null()
        & pl.col("epa").is_not_null()
    ).with_columns(
        pl.col("success").cast(pl.Float64, strict=False).fill_null(0.0),
        (pl.col("yards_gained").fill_null(0.0) >= 20).cast(pl.Float64).alias("_explosive"),
    )
    off = plays.group_by(["season","week","posteam"]).agg(
        pl.len().alias("off_early_down_plays"),
        pl.col("epa").mean().alias("off_early_down_epa"),
        pl.col("success").mean().alias("off_early_down_success_rate"),
        pl.col("epa").filter(pl.col("play_type")=="pass").mean().alias("off_early_down_pass_epa"),
        pl.col("epa").filter(pl.col("play_type")=="run").mean().alias("off_early_down_rush_epa"),
        pl.col("_explosive").mean().alias("off_early_down_explosive_rate"),
    ).rename({"posteam":"team"})
    deff = plays.group_by(["season","week","defteam"]).agg(
        pl.len().alias("def_early_down_plays"),
        pl.col("epa").mean().alias("def_early_down_epa_allowed"),
        pl.col("success").mean().alias("def_early_down_success_rate_allowed"),
        pl.col("_explosive").mean().alias("def_early_down_explosive_rate_allowed"),
    ).rename({"defteam":"team"})
    weekly = off.join(deff,on=["season","week","team"],how="full",coalesce=True)
    teams = pl.concat([
        schedule.select("game_id","season","week",pl.col("home_team").alias("team"),pl.lit("home").alias("side")),
        schedule.select("game_id","season","week",pl.col("away_team").alias("team"),pl.lit("away").alias("side")),
    ])
    hist = teams.join(weekly,on=["season","team"],how="left",suffix="_hist").filter(
        pl.col("week_hist").is_not_null() & (pl.col("week_hist") < pl.col("week"))
    )
    metrics=[c for c in weekly.columns if c not in {"season","week","team"}]
    rolled=hist.group_by(["game_id","season","week","team","side"]).agg(
        *[(pl.col(c).sum() if c.endswith("_plays") else pl.col(c).mean()).alias(c) for c in metrics],
        pl.col("week_hist").n_unique().alias("early_down_history_weeks"),
    )
    team=teams.join(rolled,on=["game_id","season","week","team","side"],how="left").with_columns(
        pl.col("early_down_history_weeks").fill_null(0),
        (pl.col("early_down_history_weeks").fill_null(0)>0).alias("early_down_known"),
    )
    m=[c for c in team.columns if c not in {"game_id","season","week","team","side"}]
    home=team.filter(pl.col("side")=="home").select("game_id",*[pl.col(c).alias(f"home_{c}") for c in m])
    away=team.filter(pl.col("side")=="away").select("game_id",*[pl.col(c).alias(f"away_{c}") for c in m])
    return schedule.select("game_id","season","week","home_team","away_team").join(home,on="game_id",how="left").join(away,on="game_id",how="left").with_columns(
        (pl.col("home_off_early_down_epa")-pl.col("away_off_early_down_epa")).alias("early_down_off_epa_difference"),
        (pl.col("away_def_early_down_epa_allowed")-pl.col("home_def_early_down_epa_allowed")).alias("early_down_def_epa_difference"),
        (pl.col("home_off_early_down_success_rate")-pl.col("away_off_early_down_success_rate")).alias("early_down_success_difference"),
    )
