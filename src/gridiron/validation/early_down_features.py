"""Validation for early-down artifacts."""
import polars as pl

REQUIRED={"game_id","season","week","home_team","away_team","home_early_down_known","away_early_down_known","early_down_off_epa_difference","early_down_def_epa_difference","early_down_success_difference"}
def validate_early_down_features(frame: pl.DataFrame) -> None:
    missing=REQUIRED.difference(frame.columns)
    if missing: raise ValueError("Early-down features are missing columns: "+", ".join(sorted(missing)))
    if frame.select(pl.col("game_id").is_duplicated().any()).item(): raise ValueError("Early-down features contain duplicate game_id values.")
