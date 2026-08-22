"""Step 83B â€” historical coverage, dispersion, and leakage validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURE_COLUMNS = (
    "pace_play_volume_advantage",
    "pace_seconds_advantage",
    "tempo_index_advantage",
)

KNOWN_COLUMNS = (
    "home_pace_tempo_known",
    "away_pace_tempo_known",
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
        "home_pace_tempo_known",
        "away_pace_tempo_known",
        "home_pregame_offensive_plays",
        "away_pregame_offensive_plays",
        "home_pregame_seconds_to_snap",
        "away_pregame_seconds_to_snap",
        "home_pregame_tempo_index",
        "away_pregame_tempo_index",
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

    week1_unknown = True
    if week1.height:
        week1_unknown = bool(
            (
                (~pl.col("home_pace_tempo_known"))
                & (~pl.col("away_pace_tempo_known"))
            )
            .all()
            .select()
            if False
            else (
                week1["home_pace_tempo_known"].not_().all()
                and week1["away_pace_tempo_known"].not_().all()
            )
        )

    week2plus_known_rate = (
        float(
            (
                week2plus["home_pace_tempo_known"]
                & week2plus["away_pace_tempo_known"]
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

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicate_count,
        "week1_rows": week1.height,
        "week1_all_unknown": week1_unknown,
        "week2plus_both_known_rate": week2plus_known_rate,
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
                f"{season}: Week 1 pace/tempo should be unknown"
            )

        if result["week2plus_both_known_rate"] < 0.95:
            warnings.append(
                f"{season}: Week 2+ both-known rate below 95%"
            )

        for column, stats in result["features"].items():
            if stats["coverage"] < 0.90:
                failures.append(
                    f"{season}: {column} coverage below 90%"
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
        "# Step 83B â€” Pace / Tempo Historical Validation",
        "",
        (
            "This report validates coverage, dispersion, and leakage safety. "
            "It does not claim predictive value."
        ),
        "",
        "## Coverage",
        "",
        "| Season | Rows | Week1 unknown | Week2+ both-known | Volume cov | Seconds cov | Tempo cov |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{'yes' if result['week1_all_unknown'] else 'no'} | "
            f"{result['week2plus_both_known_rate']:.1%} | "
            f"{result['features']['pace_play_volume_advantage']['coverage']:.1%} | "
            f"{result['features']['pace_seconds_advantage']['coverage']:.1%} | "
            f"{result['features']['tempo_index_advantage']['coverage']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Leakage contract",
            "",
            (
                "Step 83A uses prior games only. Current-game pace observations "
                "must not contribute to that game's pregame features."
            ),
            "",
            (
                "Week 1 is intentionally unknown. From Week 2 onward, prior-game "
                "history is permitted."
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
            "**PASS** â€” the pace/tempo family is technically researchable."
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
        default=Path("data/curated/pace_tempo_features"),
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
            / f"pace_tempo_features_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Step 83A artifact for {season}: {path}"
            )
        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "83B",
        "seasons": seasons,
    }

    failures, warnings = evaluate(report)
    report["failures"] = failures
    report["warnings"] = warnings
    report["status"] = "PASS" if not failures else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = (
        args.output_dir
        / "pace_tempo_validation_83b.json"
    )
    md_path = (
        args.output_dir
        / "pace_tempo_validation_83b.md"
    )

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON â€” STEP 83B PACE / TEMPO HISTORICAL VALIDATION")
    print("=" * 96)

    for season, result in seasons.items():
        print(
            f"{season}: rows={result['rows']}  "
            f"week1_unknown={result['week1_all_unknown']}  "
            f"week2+={result['week2plus_both_known_rate']:.1%}  "
            f"volume={result['features']['pace_play_volume_advantage']['coverage']:.1%}  "
            f"seconds={result['features']['pace_seconds_advantage']['coverage']:.1%}  "
            f"tempo={result['features']['tempo_index_advantage']['coverage']:.1%}"
        )

    print("-" * 96)
    print(f"STATUS: {report['status']}")

    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")

    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 96)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
