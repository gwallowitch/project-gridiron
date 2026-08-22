
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

SEASONS = (2022, 2023, 2024, 2025)
FEATURE_COLUMNS = (
    "explosive_off_rate_difference",
    "explosive_suppression_advantage",
    "chunk_off_rate_difference",
    "chunk_suppression_advantage",
    "explosive_yards_share_difference",
)
SAMPLE_COLUMNS = (
    "home_off_scrimmage_plays",
    "away_off_scrimmage_plays",
    "home_def_scrimmage_plays_faced",
    "away_def_scrimmage_plays_faced",
    "home_explosive_suppression_history_weeks",
    "away_explosive_suppression_history_weeks",
)

@dataclass(frozen=True, slots=True)
class SeasonValidation:
    season: int
    rows: int
    home_known: float
    away_known: float
    feature_coverage: dict[str, float]
    feature_mean: dict[str, float | None]
    feature_std: dict[str, float | None]
    sample_means: dict[str, float | None]

def artifact_path(root: Path, season: int) -> Path:
    return root / "data" / "curated" / "explosive_suppression_features" / f"explosive_suppression_features_{season}.parquet"

def _mean(df: pl.DataFrame, c: str):
    v = df[c].mean()
    return None if v is None else float(v)

def _std(df: pl.DataFrame, c: str):
    v = df[c].std()
    return None if v is None else float(v)

def validate_season(path: Path, season: int) -> SeasonValidation:
    if not path.exists():
        raise FileNotFoundError(f"Missing explosive-suppression artifact: {path}")
    df = pl.read_parquet(path)
    required = {"game_id", "season", "home_explosive_suppression_known", "away_explosive_suppression_known", *FEATURE_COLUMNS, *SAMPLE_COLUMNS}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{season} artifact is missing columns: " + ", ".join(sorted(missing)))
    if df["game_id"].n_unique() != df.height:
        raise ValueError(f"{season} artifact contains duplicate game_id values.")
    seasons = sorted(df["season"].drop_nulls().unique().to_list())
    if seasons != [season]:
        raise ValueError(f"{season} artifact has unexpected season values: {seasons}")
    return SeasonValidation(
        season=season,
        rows=df.height,
        home_known=float(df["home_explosive_suppression_known"].mean()),
        away_known=float(df["away_explosive_suppression_known"].mean()),
        feature_coverage={c: float(df[c].is_not_null().mean()) for c in FEATURE_COLUMNS},
        feature_mean={c: _mean(df, c) for c in FEATURE_COLUMNS},
        feature_std={c: _std(df, c) for c in FEATURE_COLUMNS},
        sample_means={c: _mean(df, c) for c in SAMPLE_COLUMNS},
    )

def _validate_cross_season(results: list[SeasonValidation]) -> None:
    if not results:
        raise ValueError("At least one season is required.")
    for r in results:
        if r.home_known < 0.90 or r.away_known < 0.90:
            raise ValueError(f"{r.season} explosive-suppression known coverage is below 90%.")
        for c, coverage in r.feature_coverage.items():
            if coverage < 0.85:
                raise ValueError(f"{r.season} {c} coverage is below 85%.")
        if (r.sample_means["home_explosive_suppression_history_weeks"] or 0) < 5:
            raise ValueError(f"{r.season} explosive-suppression history depth is unexpectedly low.")
        if (r.sample_means["home_off_scrimmage_plays"] or 0) < 150:
            raise ValueError(f"{r.season} offensive scrimmage-play sample depth is too low.")
        if (r.sample_means["home_def_scrimmage_plays_faced"] or 0) < 150:
            raise ValueError(f"{r.season} defensive scrimmage-play sample depth is too low.")
        for c, v in r.feature_mean.items():
            if v is None:
                raise ValueError(f"{r.season} {c} has no usable observations.")
        for c, v in r.feature_std.items():
            if v is None or v <= 0:
                raise ValueError(f"{r.season} {c} has no dispersion.")

def validate_history(project_root: Path = Path("."), seasons: tuple[int, ...] = SEASONS):
    results = [validate_season(artifact_path(project_root, s), s) for s in seasons]
    _validate_cross_season(results)
    return results

def format_report(results):
    lines = ["=" * 100, "PROJECT GRIDIRON — EXPLOSIVE-SUPPRESSION HISTORICAL VALIDATION", "=" * 100]
    for r in results:
        lines += [f"Season {r.season}", f"Rows...................... {r.rows}", f"Home known................ {r.home_known:.1%}", f"Away known................ {r.away_known:.1%}", "Feature coverage:"]
        for c, v in r.feature_coverage.items():
            lines.append(f"  {c:<48} {v:.1%}")
        lines.append("Feature means / std:")
        for c in FEATURE_COLUMNS:
            lines.append(f"  {c:<48} mean={r.feature_mean[c]: .4f}  std={r.feature_std[c]: .4f}")
        lines.append("Sample depth means:")
        for c, v in r.sample_means.items():
            lines.append(f"  {c:<48} {v:.2f}")
        lines.append("-" * 100)
    lines += ["STATUS: PASS", "=" * 100]
    return "\n".join(lines)

def main() -> int:
    print(format_report(validate_history(Path("."))))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
