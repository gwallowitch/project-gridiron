"""Historical validation for Step 79B opponent-adjusted features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURES = (
    "opponent_adjusted_off_epa_difference",
    "opponent_adjusted_def_epa_difference",
    "offensive_schedule_difficulty_advantage",
    "defensive_schedule_difficulty_advantage",
)

KNOWN_COLUMNS = (
    "home_opponent_adjusted_known",
    "away_opponent_adjusted_known",
)

DEPTH_COLUMNS = (
    "home_opponent_adjusted_history_weeks",
    "away_opponent_adjusted_history_weeks",
    "home_opponent_adjusted_opponents",
    "away_opponent_adjusted_opponents",
)


def _float(value: object) -> float | None:
    return None if value is None else float(value)


def _quantile(series: pl.Series, q: float) -> float | None:
    clean = series.drop_nulls()
    if clean.len() == 0:
        return None
    value = clean.quantile(q, interpolation="linear")
    return None if value is None else float(value)


def validate_season(path: Path, season: int) -> dict[str, object]:
    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        "week",
        *KNOWN_COLUMNS,
        *DEPTH_COLUMNS,
        *FEATURES,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path} is missing required columns: "
            + ", ".join(sorted(missing))
        )

    seasons = sorted(frame["season"].drop_nulls().unique().to_list())
    if seasons != [season]:
        raise ValueError(
            f"{path} contains unexpected season values: {seasons}"
        )

    duplicates = frame.height - frame["game_id"].n_unique()
    if duplicates:
        raise ValueError(
            f"{path} contains {duplicates} duplicate game_id rows."
        )

    both_known = (
        frame.select(
            pl.col("home_opponent_adjusted_known")
            & pl.col("away_opponent_adjusted_known")
        )
        .to_series()
    )
    mature = frame.filter(pl.col("week") >= 4)
    mature_known = (
        mature.select(
            pl.col("home_opponent_adjusted_known")
            & pl.col("away_opponent_adjusted_known")
        )
        .to_series()
    )

    feature_stats: dict[str, object] = {}
    for name in FEATURES:
        series = frame[name]
        clean = series.drop_nulls()
        feature_stats[name] = {
            "coverage": float(series.is_not_null().mean()),
            "mean": _float(clean.mean()),
            "std": _float(clean.std()),
            "p05": _quantile(clean, 0.05),
            "p25": _quantile(clean, 0.25),
            "median": _quantile(clean, 0.50),
            "p75": _quantile(clean, 0.75),
            "p95": _quantile(clean, 0.95),
            "nonzero_rate": (
                float((clean.abs() > 1e-12).mean())
                if clean.len()
                else 0.0
            ),
        }

    depth = {}
    for name in DEPTH_COLUMNS:
        series = frame[name]
        depth[name] = {
            "mean": _float(series.mean()),
            "median": _quantile(series, 0.50),
            "p25": _quantile(series, 0.25),
            "p75": _quantile(series, 0.75),
            "max": _float(series.max()),
        }

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicates,
        "both_known_rate": float(both_known.mean() or 0.0),
        "week4_plus_both_known_rate": float(mature_known.mean() or 0.0),
        "features": feature_stats,
        "depth": depth,
    }


def evaluate(report: dict[str, object]) -> list[str]:
    failures: list[str] = []

    for season_key, result in report["seasons"].items():
        season = int(season_key)

        if result["rows"] < 250:
            failures.append(
                f"{season}: fewer than 250 schedule rows"
            )

        if result["week4_plus_both_known_rate"] < 0.85:
            failures.append(
                f"{season}: week-4+ both-known coverage below 85%"
            )

        for name, stats in result["features"].items():
            if stats["coverage"] < 0.70:
                failures.append(
                    f"{season} {name}: total coverage below 70%"
                )

            std = stats["std"]
            if std is None or std <= 1e-9:
                failures.append(
                    f"{season} {name}: no meaningful dispersion"
                )

            if stats["nonzero_rate"] < 0.50:
                failures.append(
                    f"{season} {name}: fewer than 50% non-zero observations"
                )

        home_weeks = result["depth"][
            "home_opponent_adjusted_history_weeks"
        ]["mean"]
        home_opponents = result["depth"][
            "home_opponent_adjusted_opponents"
        ]["mean"]

        if home_weeks is None or home_weeks < 5.0:
            failures.append(
                f"{season}: average home history depth below 5 weeks"
            )

        if home_opponents is None or home_opponents < 4.0:
            failures.append(
                f"{season}: average home opponent depth below 4 opponents"
            )

    return failures


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 79B — Opponent-Adjusted Historical Validation",
        "",
        (
            "This is a technical coverage/dispersion gate only. It does not "
            "claim predictive lift."
        ),
        "",
        "## Coverage",
        "",
        "| Season | Rows | Both known | Week 4+ both known |",
        "| ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{result['both_known_rate']:.1%} | "
            f"{result['week4_plus_both_known_rate']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Feature dispersion",
            "",
            "| Season | Feature | Coverage | Mean | Std | P05 | Median | P95 | Non-zero |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    def fmt(value: float | None) -> str:
        return "NA" if value is None else f"{value:.4f}"

    for season, result in report["seasons"].items():
        for name, stats in result["features"].items():
            lines.append(
                f"| {season} | `{name}` | "
                f"{stats['coverage']:.1%} | "
                f"{fmt(stats['mean'])} | "
                f"{fmt(stats['std'])} | "
                f"{fmt(stats['p05'])} | "
                f"{fmt(stats['median'])} | "
                f"{fmt(stats['p95'])} | "
                f"{stats['nonzero_rate']:.1%} |"
            )

    lines.extend(["", "## Gate", ""])
    failures = report["failures"]

    if failures:
        lines.append("**FAIL**")
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append(
            "**PASS** — the opponent-adjusted family is technically healthy "
            "enough for controlled experiment wiring."
        )

    lines.extend(
        [
            "",
            (
                "A PASS here means only that the artifacts are researchable. "
                "It does not promote any opponent-adjusted signal."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        default=[2022, 2023, 2024, 2025],
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(
            "data/curated/opponent_adjusted_features"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    seasons: dict[str, object] = {}
    for season in args.seasons:
        path = (
            args.input_dir
            / f"opponent_adjusted_features_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Step 79A artifact for {season}: {path}"
            )

        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "79B",
        "seasons": seasons,
    }
    report["failures"] = evaluate(report)
    report["status"] = (
        "PASS" if not report["failures"] else "FAIL"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = (
        args.output_dir
        / "opponent_adjusted_validation_79b.json"
    )
    md_path = (
        args.output_dir
        / "opponent_adjusted_validation_79b.md"
    )

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 92)
    print(
        "PROJECT GRIDIRON — STEP 79B "
        "OPPONENT-ADJUSTED HISTORICAL VALIDATION"
    )
    print("=" * 92)

    for season, result in seasons.items():
        print(
            f"{season}: rows={result['rows']}  "
            f"both-known={result['both_known_rate']:.1%}  "
            f"week4+-known="
            f"{result['week4_plus_both_known_rate']:.1%}"
        )

    print("-" * 92)
    print(f"STATUS: {report['status']}")

    if report["failures"]:
        for failure in report["failures"]:
            print(f"FAIL: {failure}")

    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 92)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
