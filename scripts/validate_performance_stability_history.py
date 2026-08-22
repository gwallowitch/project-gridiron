"""Step 84B â€” performance-stability historical validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURE_COLUMNS = (
    "stability_advantage",
    "recent_margin_advantage",
    "close_game_experience_advantage",
)

KNOWN_COLUMNS = (
    "home_performance_stability_known",
    "away_performance_stability_known",
)


def _stats(series: pl.Series) -> dict[str, float | None]:
    clean = series.drop_nulls()
    return {
        "coverage": float(series.is_not_null().mean()),
        "mean": None if clean.len() == 0 else float(clean.mean()),
        "std": None if clean.len() == 0 else float(clean.std()),
        "min": None if clean.len() == 0 else float(clean.min()),
        "max": None if clean.len() == 0 else float(clean.max()),
        "p05": None if clean.len() == 0 else float(clean.quantile(0.05)),
        "median": None if clean.len() == 0 else float(clean.median()),
        "p95": None if clean.len() == 0 else float(clean.quantile(0.95)),
    }


def validate_season(path: Path, season: int) -> dict[str, object]:
    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "home_performance_stability_known",
        "away_performance_stability_known",
        "home_mean_point_differential",
        "away_mean_point_differential",
        "home_point_differential_std",
        "away_point_differential_std",
        "home_mean_absolute_margin",
        "away_mean_absolute_margin",
        "home_close_game_rate",
        "away_close_game_rate",
        *FEATURE_COLUMNS,
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

    duplicate_count = frame.height - frame["game_id"].n_unique()
    if duplicate_count:
        raise ValueError(
            f"{path} contains {duplicate_count} duplicate game_id rows."
        )

    week1 = frame.filter(pl.col("week") == 1)
    week2 = frame.filter(pl.col("week") == 2)
    week3plus = frame.filter(pl.col("week") >= 3)

    week1_unknown = (
        bool(
            week1["home_performance_stability_known"].not_().all()
            and week1["away_performance_stability_known"].not_().all()
        )
        if week1.height
        else True
    )

    # Margin and close-game features require one prior game.
    week2_margin_known = (
        float(
            (
                week2["home_mean_point_differential"].is_not_null()
                & week2["away_mean_point_differential"].is_not_null()
            ).mean()
        )
        if week2.height
        else 0.0
    )

    # Stability standard deviation requires two prior games.
    week2_stability_unknown = (
        bool(
            week2["stability_advantage"].is_null().all()
        )
        if week2.height
        else True
    )

    week3plus_stability_known = (
        float(
            week3plus["stability_advantage"].is_not_null().mean()
        )
        if week3plus.height
        else 0.0
    )

    non_finite = {}
    for column in FEATURE_COLUMNS:
        non_finite[column] = int(
            frame.filter(
                pl.col(column).is_not_null()
                & (~pl.col(column).is_finite())
            ).height
        )

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicate_count,
        "week1_rows": week1.height,
        "week1_all_unknown": week1_unknown,
        "week2_margin_known_rate": week2_margin_known,
        "week2_stability_all_unknown": week2_stability_unknown,
        "week3plus_stability_known_rate": week3plus_stability_known,
        "known_rates": {
            column: float(frame[column].mean() or 0.0)
            for column in KNOWN_COLUMNS
        },
        "features": {
            column: _stats(frame[column])
            for column in FEATURE_COLUMNS
        },
        "non_finite_counts": non_finite,
    }


def evaluate(report: dict[str, object]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for season_key, result in report["seasons"].items():
        season = int(season_key)

        if result["rows"] < 250:
            failures.append(f"{season}: fewer than 250 rows")

        if result["duplicate_game_ids"] != 0:
            failures.append(f"{season}: duplicate game IDs present")

        if not result["week1_all_unknown"]:
            failures.append(
                f"{season}: Week 1 performance stability should be unknown"
            )

        if result["week2_margin_known_rate"] < 0.95:
            warnings.append(
                f"{season}: Week 2 margin coverage below 95%"
            )

        if not result["week2_stability_all_unknown"]:
            failures.append(
                f"{season}: Week 2 stability should be unknown "
                "because standard deviation requires two prior games"
            )

        if result["week3plus_stability_known_rate"] < 0.95:
            warnings.append(
                f"{season}: Week 3+ stability coverage below 95%"
            )

        for column, stats in result["features"].items():
            minimum_coverage = (
                0.85 if column == "stability_advantage" else 0.90
            )
            if stats["coverage"] < minimum_coverage:
                failures.append(
                    f"{season}: {column} coverage below "
                    f"{minimum_coverage:.0%}"
                )

            if stats["std"] is None or stats["std"] == 0.0:
                failures.append(
                    f"{season}: {column} has no dispersion"
                )

            if result["non_finite_counts"][column] != 0:
                failures.append(
                    f"{season}: {column} contains non-finite values"
                )

    return failures, warnings


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 84B â€” Performance Stability Historical Validation",
        "",
        (
            "This report validates coverage, dispersion, chronology, and "
            "no-leakage behavior. It does not claim predictive value."
        ),
        "",
        "## Coverage",
        "",
        (
            "| Season | Rows | Week1 unknown | Week2 margin known | "
            "Week2 stability unknown | Week3+ stability known | "
            "Stability cov | Margin cov | Close cov |"
        ),
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{'yes' if result['week1_all_unknown'] else 'no'} | "
            f"{result['week2_margin_known_rate']:.1%} | "
            f"{'yes' if result['week2_stability_all_unknown'] else 'no'} | "
            f"{result['week3plus_stability_known_rate']:.1%} | "
            f"{result['features']['stability_advantage']['coverage']:.1%} | "
            f"{result['features']['recent_margin_advantage']['coverage']:.1%} | "
            f"{result['features']['close_game_experience_advantage']['coverage']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Leakage contract",
            "",
            (
                "All Step 84A features are derived from completed prior games "
                "only. Current-game scores must not contribute to pregame "
                "features for that same game."
            ),
            "",
            (
                "Week 1 is intentionally unknown. Margin and close-game "
                "features become available after one prior game. Stability "
                "standard deviation becomes available only after two prior games."
            ),
            "",
            "## Gate",
            "",
        ]
    )

    if report["failures"]:
        lines.append("**FAIL**")
        lines.extend(f"- {item}" for item in report["failures"])
    else:
        lines.append(
            "**PASS** â€” the performance-stability family is technically "
            "researchable."
        )

    if report["warnings"]:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])

    return "\n".join(lines) + "\n"


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
        default=Path("data/curated/performance_stability_features"),
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
            / f"performance_stability_features_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Step 84A artifact for {season}: {path}"
            )
        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "84B",
        "seasons": seasons,
    }

    failures, warnings = evaluate(report)
    report["failures"] = failures
    report["warnings"] = warnings
    report["status"] = "PASS" if not failures else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "performance_stability_validation_84b.json"
    md_path = args.output_dir / "performance_stability_validation_84b.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print("=" * 104)
    print("PROJECT GRIDIRON â€” STEP 84B PERFORMANCE STABILITY HISTORICAL VALIDATION")
    print("=" * 104)

    for season, result in seasons.items():
        print(
            f"{season}: rows={result['rows']}  "
            f"week1_unknown={result['week1_all_unknown']}  "
            f"week2_margin={result['week2_margin_known_rate']:.1%}  "
            f"week2_stab_unknown={result['week2_stability_all_unknown']}  "
            f"week3+_stab={result['week3plus_stability_known_rate']:.1%}  "
            f"stability={result['features']['stability_advantage']['coverage']:.1%}  "
            f"margin={result['features']['recent_margin_advantage']['coverage']:.1%}  "
            f"close={result['features']['close_game_experience_advantage']['coverage']:.1%}"
        )

    print("-" * 104)
    print(f"STATUS: {report['status']}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 104)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

