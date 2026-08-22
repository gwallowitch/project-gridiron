"""Historical validation for Step 78B recent-form features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURES = (
    "recent_off_epa_difference",
    "recent_def_epa_advantage",
    "off_epa_trend_difference",
    "def_epa_trend_advantage",
    "off_success_trend_difference",
    "def_success_trend_advantage",
)

KNOWN_COLUMNS = ("home_recent_form_known", "away_recent_form_known")
RECENT_WEEK_COLUMNS = ("home_recent_form_weeks", "away_recent_form_weeks")


def _quantile(series: pl.Series, q: float) -> float | None:
    clean = series.drop_nulls()
    if clean.len() == 0:
        return None
    value = clean.quantile(q, interpolation="linear")
    return None if value is None else float(value)


def _float(value: object) -> float | None:
    return None if value is None else float(value)


def validate_season(path: Path, season: int) -> dict[str, object]:
    frame = pl.read_parquet(path)
    required = {
        "game_id",
        "season",
        "week",
        *KNOWN_COLUMNS,
        *RECENT_WEEK_COLUMNS,
        *FEATURES,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path} is missing required columns: "
            + ", ".join(sorted(missing))
        )

    season_values = frame["season"].drop_nulls().unique().to_list()
    if season_values != [season]:
        raise ValueError(
            f"{path} contains unexpected season values: {season_values}"
        )

    duplicates = frame.height - frame["game_id"].n_unique()
    if duplicates:
        raise ValueError(f"{path} contains {duplicates} duplicate game_id rows.")

    known = (
        frame.select(
            pl.col("home_recent_form_known")
            & pl.col("away_recent_form_known")
        )
        .to_series()
    )
    both_known = float(known.mean() or 0.0)

    week_three_plus = frame.filter(pl.col("week") >= 3)
    mature_known = (
        week_three_plus.select(
            pl.col("home_recent_form_known")
            & pl.col("away_recent_form_known")
        )
        .to_series()
    )
    mature_coverage = float(mature_known.mean() or 0.0)

    features: dict[str, object] = {}
    for name in FEATURES:
        series = frame[name]
        non_null = series.drop_nulls()
        features[name] = {
            "coverage": float(series.is_not_null().mean()),
            "mean": _float(non_null.mean()),
            "std": _float(non_null.std()),
            "min": _float(non_null.min()),
            "p05": _quantile(non_null, 0.05),
            "p25": _quantile(non_null, 0.25),
            "median": _quantile(non_null, 0.50),
            "p75": _quantile(non_null, 0.75),
            "p95": _quantile(non_null, 0.95),
            "max": _float(non_null.max()),
            "nonzero_rate": (
                float((non_null.abs() > 1e-12).mean())
                if non_null.len()
                else 0.0
            ),
        }

    week_depth = {}
    for name in RECENT_WEEK_COLUMNS:
        series = frame[name]
        week_depth[name] = {
            "mean": _float(series.mean()),
            "median": _quantile(series, 0.50),
            "max": _float(series.max()),
        }

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicates,
        "both_recent_known_rate": both_known,
        "week3_plus_both_known_rate": mature_coverage,
        "week_depth": week_depth,
        "features": features,
    }


def evaluate(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    seasons = report["seasons"]

    for season_key, result in seasons.items():
        season = int(season_key)
        if result["rows"] < 250:
            failures.append(f"{season}: fewer than 250 schedule rows")

        if result["week3_plus_both_known_rate"] < 0.90:
            failures.append(
                f"{season}: week-3+ recent-form coverage below 90%"
            )

        for name, stats in result["features"].items():
            if stats["coverage"] < 0.75:
                failures.append(
                    f"{season} {name}: total coverage below 75%"
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

    return failures


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 78B — Recent-Form Historical Validation",
        "",
        ("This report validates coverage and dispersion only. It does not "
         "claim predictive value."),
        "",
        "## Coverage",
        "",
        "| Season | Rows | Both known | Week 3+ both known |",
        "| ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{result['both_recent_known_rate']:.1%} | "
            f"{result['week3_plus_both_known_rate']:.1%} |"
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

    for season, result in report["seasons"].items():
        for name, stats in result["features"].items():
            def fmt(value: float | None) -> str:
                return "NA" if value is None else f"{value:.4f}"

            lines.append(
                f"| {season} | `{name}` | {stats['coverage']:.1%} | "
                f"{fmt(stats['mean'])} | {fmt(stats['std'])} | "
                f"{fmt(stats['p05'])} | {fmt(stats['median'])} | "
                f"{fmt(stats['p95'])} | {stats['nonzero_rate']:.1%} |"
            )

    lines.extend(["", "## Gate", ""])
    failures = report["failures"]
    if failures:
        lines.append("**FAIL**")
        lines.extend(f"- {item}" for item in failures)
    else:
        lines.append(
            "**PASS** — historical coverage and dispersion are healthy enough "
            "to proceed to controlled experiment wiring."
        )

    lines.extend(
        [
            "",
            ("Passing this gate means the feature family is technically "
             "researchable. It does **not** promote any recent-form signal."),
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
        default=Path("data/curated/recent_form_features"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    seasons: dict[str, object] = {}
    for season in args.seasons:
        path = args.input_dir / f"recent_form_features_{season}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing 78A artifact for {season}: {path}"
            )
        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "78B",
        "seasons": seasons,
    }
    report["failures"] = evaluate(report)
    report["status"] = "PASS" if not report["failures"] else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "recent_form_validation_78b.json"
    md_path = args.output_dir / "recent_form_validation_78b.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print("=" * 88)
    print("PROJECT GRIDIRON — STEP 78B RECENT-FORM HISTORICAL VALIDATION")
    print("=" * 88)
    for season, result in seasons.items():
        print(
            f"{season}: rows={result['rows']}  "
            f"both-known={result['both_recent_known_rate']:.1%}  "
            f"week3+-known={result['week3_plus_both_known_rate']:.1%}"
        )
    print("-" * 88)
    print(f"STATUS: {report['status']}")
    if report["failures"]:
        for failure in report["failures"]:
            print(f"FAIL: {failure}")
    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 88)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

