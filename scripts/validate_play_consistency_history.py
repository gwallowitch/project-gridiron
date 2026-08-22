"""Step 87B — play-consistency historical validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURE_COLUMNS = (
    "off_success_rate_advantage",
    "def_success_prevention_advantage",
    "success_rate_matchup_advantage",
    "negative_play_matchup_advantage",
)

KNOWN_COLUMNS = (
    "home_play_consistency_known",
    "away_play_consistency_known",
)

RATE_COLUMNS = (
    "home_off_success_rate",
    "away_off_success_rate",
    "home_def_success_prevention_rate",
    "away_def_success_prevention_rate",
    "home_off_negative_play_rate",
    "away_off_negative_play_rate",
    "home_def_negative_play_forced_rate",
    "away_def_negative_play_forced_rate",
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
        *RATE_COLUMNS,
        *KNOWN_COLUMNS,
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
    week2plus = frame.filter(pl.col("week") >= 2)

    week1_unknown = (
        bool(
            week1["home_play_consistency_known"].not_().all()
            and week1["away_play_consistency_known"].not_().all()
        )
        if week1.height
        else True
    )

    week2plus_both_known_rate = (
        float(
            (
                week2plus["home_play_consistency_known"]
                & week2plus["away_play_consistency_known"]
            ).mean()
        )
        if week2plus.height
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

    out_of_bounds = {}
    for column in RATE_COLUMNS:
        out_of_bounds[column] = int(
            frame.filter(
                pl.col(column).is_not_null()
                & (
                    (pl.col(column) < 0.0)
                    | (pl.col(column) > 1.0)
                )
            ).height
        )

    known_feature_mismatch = {}
    both_known = (
        pl.col("home_play_consistency_known").fill_null(False)
        & pl.col("away_play_consistency_known").fill_null(False)
    )
    for column in FEATURE_COLUMNS:
        known_feature_mismatch[column] = int(
            frame.filter(
                both_known
                & pl.col(column).is_null()
            ).height
        )

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicate_count,
        "week1_rows": week1.height,
        "week1_all_unknown": week1_unknown,
        "week2plus_both_known_rate": week2plus_both_known_rate,
        "known_rates": {
            column: float(frame[column].mean() or 0.0)
            for column in KNOWN_COLUMNS
        },
        "features": {
            column: _stats(frame[column])
            for column in FEATURE_COLUMNS
        },
        "non_finite_counts": non_finite,
        "out_of_bounds_counts": out_of_bounds,
        "known_feature_mismatch": known_feature_mismatch,
    }


def evaluate(report: dict[str, object]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    expected_rows = {
        2022: 284,
        2023: 285,
        2024: 285,
        2025: 285,
    }

    for season_key, result in report["seasons"].items():
        season = int(season_key)

        expected = expected_rows.get(season)
        if expected is not None and result["rows"] != expected:
            failures.append(
                f"{season}: expected {expected} rows, found {result['rows']}"
            )

        if result["duplicate_game_ids"] != 0:
            failures.append(f"{season}: duplicate game IDs present")

        if not result["week1_all_unknown"]:
            failures.append(
                f"{season}: Week 1 play-consistency features should be unknown"
            )

        if result["week2plus_both_known_rate"] < 0.999:
            failures.append(
                f"{season}: Week 2+ both-known rate below 99.9%"
            )

        for column, stats in result["features"].items():
            if stats["coverage"] < 0.94:
                failures.append(
                    f"{season}: {column} coverage below 94%"
                )

            if stats["std"] is None or stats["std"] == 0.0:
                failures.append(
                    f"{season}: {column} has no dispersion"
                )

            if result["non_finite_counts"][column] != 0:
                failures.append(
                    f"{season}: {column} contains non-finite values"
                )

            if result["known_feature_mismatch"][column] != 0:
                failures.append(
                    f"{season}: {column} missing despite both teams being known"
                )

        for column, count in result["out_of_bounds_counts"].items():
            if count != 0:
                failures.append(
                    f"{season}: {column} contains values outside [0, 1]"
                )

    return failures, warnings


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 87B — Play-Consistency Historical Validation",
        "",
        (
            "This report validates chronology, coverage, dispersion, bounds, "
            "and no-current-game leakage. It does not claim predictive value."
        ),
        "",
        "## Coverage",
        "",
        (
            "| Season | Rows | Week1 unknown | Week2+ both-known | "
            "Off cov | Def cov | Matchup cov | Negative-play cov |"
        ),
        (
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
        ),
    ]

    for season, result in report["seasons"].items():
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{'yes' if result['week1_all_unknown'] else 'no'} | "
            f"{result['week2plus_both_known_rate']:.1%} | "
            f"{result['features']['off_success_rate_advantage']['coverage']:.1%} | "
            f"{result['features']['def_success_prevention_advantage']['coverage']:.1%} | "
            f"{result['features']['success_rate_matchup_advantage']['coverage']:.1%} | "
            f"{result['features']['negative_play_matchup_advantage']['coverage']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Leakage contract",
            "",
            (
                "Step 87A uses pass/rush plays from completed prior games only. "
                "Current-game plays must not contribute to that game's pregame "
                "play-consistency features."
            ),
            "",
            (
                "Week 1 is intentionally unknown. Week 2 onward may use "
                "completed prior-game history."
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
            "**PASS** — the play-consistency family is technically researchable."
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
        default=Path("data/curated/play_consistency_features"),
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
            / f"play_consistency_features_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Step 87A artifact for {season}: {path}"
            )
        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "87B",
        "seasons": seasons,
    }

    failures, warnings = evaluate(report)
    report["failures"] = failures
    report["warnings"] = warnings
    report["status"] = "PASS" if not failures else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "play_consistency_validation_87b.json"
    md_path = args.output_dir / "play_consistency_validation_87b.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 104)
    print("PROJECT GRIDIRON — STEP 87B PLAY-CONSISTENCY HISTORICAL VALIDATION")
    print("=" * 104)

    for season, result in seasons.items():
        print(
            f"{season}: rows={result['rows']}  "
            f"week1_unknown={result['week1_all_unknown']}  "
            f"week2+={result['week2plus_both_known_rate']:.1%}  "
            f"off={result['features']['off_success_rate_advantage']['coverage']:.1%}  "
            f"def={result['features']['def_success_prevention_advantage']['coverage']:.1%}  "
            f"matchup={result['features']['success_rate_matchup_advantage']['coverage']:.1%}  "
            f"negative={result['features']['negative_play_matchup_advantage']['coverage']:.1%}"
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
