"""Leakage-safe historical quarterback intelligence."""
from __future__ import annotations

import polars as pl

RAW = {"season","week","team","player_id","player_display_name","position",
       "attempts","completions","passing_yards","passing_tds","passing_interceptions"}
NORM = {"season","week","team","player_id","qb_name","attempts","completions",
        "passing_yards","passing_tds","interceptions"}
LEAGUE_PRIOR_EFFICIENCY = 6.0
PRIOR_ATTEMPTS = 75.0
RATING_MULTIPLIER = 0.75
MIN_RATING = -6.0
MAX_RATING = 6.0

def normalize_weekly_qb_stats(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize raw nflreadpy or already-normalized QB stats."""
    cols = set(frame.columns)
    if NORM.issubset(cols):
        return frame.select(
            pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
            pl.col("team").cast(pl.String), pl.col("player_id").cast(pl.String),
            pl.col("qb_name").cast(pl.String),
            pl.col("attempts").fill_null(0).cast(pl.Float64),
            pl.col("completions").fill_null(0).cast(pl.Float64),
            pl.col("passing_yards").fill_null(0).cast(pl.Float64),
            pl.col("passing_tds").fill_null(0).cast(pl.Float64),
            pl.col("interceptions").fill_null(0).cast(pl.Float64),
        ).filter(pl.col("week") > 0).sort(["season","week","team","player_id"])

    missing = RAW.difference(cols)
    if missing:
        raise ValueError("Weekly QB stats are missing columns: " + ", ".join(sorted(missing)))

    result = frame.filter(pl.col("position") == "QB").select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
        pl.col("team").cast(pl.String), pl.col("player_id").cast(pl.String),
        pl.col("player_display_name").cast(pl.String).alias("qb_name"),
        pl.col("attempts").fill_null(0).cast(pl.Float64),
        pl.col("completions").fill_null(0).cast(pl.Float64),
        pl.col("passing_yards").fill_null(0).cast(pl.Float64),
        pl.col("passing_tds").fill_null(0).cast(pl.Float64),
        pl.col("passing_interceptions").fill_null(0).cast(pl.Float64).alias("interceptions"),
    ).filter(pl.col("week") > 0).sort(["season","week","team","player_id"])
    if result.height == 0:
        raise ValueError("Weekly QB stats contain no quarterback rows.")
    return result

def build_prior_starter_assignments(weekly_stats: pl.DataFrame, schedule: pl.DataFrame) -> pl.DataFrame:
    stats = normalize_weekly_qb_stats(weekly_stats)
    primary = stats.sort(
        ["season","week","team","attempts","player_id"],
        descending=[False,False,False,True,False]
    ).group_by(["season","week","team"], maintain_order=True).first().select(
        "season","week","team","player_id","qb_name")
    teams = pl.concat([
        schedule.select("season","week",pl.col("home_team").alias("team")),
        schedule.select("season","week",pl.col("away_team").alias("team")),
    ]).unique().sort(["season","team","week"])
    rows = []
    for row in teams.iter_rows(named=True):
        prior = primary.filter(
            (pl.col("season")==row["season"]) &
            (pl.col("team")==row["team"]) &
            (pl.col("week")<row["week"])
        ).sort("week", descending=True)
        if prior.height:
            s = prior.row(0, named=True)
            rows.append({"season":row["season"],"week":row["week"],"team":row["team"],
                         "qb_name":s["qb_name"],"player_id":s["player_id"],"source_week":s["week"]})
        else:
            rows.append({"season":row["season"],"week":row["week"],"team":row["team"],
                         "qb_name":"UNKNOWN","player_id":"UNKNOWN","source_week":0})
    return pl.DataFrame(rows).sort(["season","week","team"])

def build_leakage_safe_weekly_ratings(weekly_stats: pl.DataFrame, schedule: pl.DataFrame) -> pl.DataFrame:
    stats = normalize_weekly_qb_stats(weekly_stats)
    assignments = build_prior_starter_assignments(stats, schedule)
    rows = []
    for a in assignments.iter_rows(named=True):
        season, week, pid = int(a["season"]), int(a["week"]), str(a["player_id"])
        league = stats.filter((pl.col("season")==season)&(pl.col("week")<week))
        league_eff = _efficiency(league)
        if pid == "UNKNOWN":
            attempts, qb_eff, rating = 0.0, league_eff, 0.0
        else:
            prior = league.filter(pl.col("player_id")==pid)
            attempts = float(prior["attempts"].sum())
            qb_eff = _efficiency(prior)
            shrink = attempts / (attempts + PRIOR_ATTEMPTS)
            rating = max(MIN_RATING, min(MAX_RATING,
                (qb_eff-league_eff)*RATING_MULTIPLIER*shrink))
        rows.append({"season":season,"week":week,"team":a["team"],"player_id":pid,
                     "qb_name":a["qb_name"],"rating":float(rating),
                     "prior_attempts":float(attempts),"prior_efficiency":float(qb_eff),
                     "league_prior_efficiency":float(league_eff),"source_week":int(a["source_week"])})
    return pl.DataFrame(rows).sort(["season","week","team"])

def _efficiency(frame: pl.DataFrame) -> float:
    attempts = float(frame["attempts"].sum()) if frame.height else 0.0
    if attempts <= 0:
        return LEAGUE_PRIOR_EFFICIENCY
    return (float(frame["passing_yards"].sum())
            + 20.0*float(frame["passing_tds"].sum())
            - 45.0*float(frame["interceptions"].sum())) / attempts
