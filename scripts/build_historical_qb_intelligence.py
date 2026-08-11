"""Build 2022-2025 leakage-safe QB intelligence from nflverse data."""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.features.qb.historical_features import build_historical_qb_features
from gridiron.features.qb.history import build_leakage_safe_weekly_ratings

DEFAULT_SEASONS = (2022, 2023, 2024, 2025)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", default=list(DEFAULT_SEASONS))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    return parser

def main() -> int:
    args = build_parser().parse_args()
    try:
        import nflreadpy as nfl
    except ImportError as exc:
        raise SystemExit(
            "nflreadpy is required. Install with: python -m pip install nflreadpy"
        ) from exc

    paths = ProjectPaths.from_root(args.project_root)
    seasons = tuple(args.seasons)
    print(f"Loading nflverse weekly player stats: {seasons}")
    weekly = nfl.load_player_stats(list(seasons), summary_level="week")

    raw_dir = paths.root / "data" / "raw" / "qb_history"
    raw_dir.mkdir(parents=True, exist_ok=True)
    weekly.write_parquet(raw_dir / "nflverse_qb_weekly.parquet")

    ratings_dir = paths.root / "data" / "curated" / "qb_weekly_ratings"
    ratings_dir.mkdir(parents=True, exist_ok=True)
    paths.qb_features.mkdir(parents=True, exist_ok=True)

    for season in seasons:
        schedule_path = paths.schedule_file(season)
        if not schedule_path.exists():
            raise FileNotFoundError(f"Missing schedule for {season}: {schedule_path}")
        schedule = pl.read_parquet(schedule_path)
        season_weekly = weekly.filter(pl.col("season") == season)
        ratings = build_leakage_safe_weekly_ratings(season_weekly, schedule)
        ratings.write_parquet(ratings_dir / f"qb_weekly_ratings_{season}.parquet")

        features = build_historical_qb_features(schedule, ratings)
        features.write_parquet(paths.qb_features_file(season))

        nonzero = features.filter(pl.col("qb_rating_difference") != 0.0).height
        known_count = features.select(
            (pl.col("home_qb_known").cast(pl.Int64).sum()
             + pl.col("away_qb_known").cast(pl.Int64).sum()).alias("known")
        ).item()
        known_rate = known_count / (2 * features.height)
        print(
            f"{season}: {features.height} games | known QB rate={known_rate:.1%} | "
            f"non-zero differences={nonzero}"
        )

    print("Historical QB intelligence complete.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
