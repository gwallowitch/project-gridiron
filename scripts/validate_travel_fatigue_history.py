"""Step 81B historical validation and neutral/international-site audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

FEATURES = (
    "away_travel_miles",
    "away_time_zone_shift_hours",
    "eastward_time_zone_shift_hours",
    "westward_time_zone_shift_hours",
)

FLAG_FEATURES = (
    "cross_country_travel",
    "long_haul_travel",
)

OPTIONAL_REST_FEATURES = (
    "short_week_away",
    "short_week_travel_miles",
    "short_week_time_zone_shift",
)

NEUTRAL_COLUMNS = (
    "neutral",
    "neutral_site",
    "is_neutral",
)

VENUE_TEXT_COLUMNS = (
    "stadium",
    "stadium_name",
    "venue",
    "location",
)

INTERNATIONAL_TERMS = (
    "london",
    "wembley",
    "tottenham",
    "germany",
    "munich",
    "frankfurt",
    "mexico",
    "azteca",
    "brazil",
    "sao paulo",
    "madrid",
    "spain",
    "dublin",
    "ireland",
)


def _float(value: object) -> float | None:
    return None if value is None else float(value)


def _quantile(series: pl.Series, q: float) -> float | None:
    clean = series.drop_nulls()
    if clean.len() == 0:
        return None
    value = clean.quantile(q, interpolation="linear")
    return None if value is None else float(value)


def _feature_stats(frame: pl.DataFrame, name: str) -> dict[str, object]:
    series = frame[name]
    clean = series.drop_nulls()
    return {
        "coverage": float(series.is_not_null().mean()),
        "mean": _float(clean.mean()),
        "std": _float(clean.std()),
        "p05": _quantile(clean, 0.05),
        "median": _quantile(clean, 0.50),
        "p95": _quantile(clean, 0.95),
        "max": _float(clean.max()),
        "nonzero_rate": (
            float((clean.abs() > 1e-12).mean())
            if clean.len()
            else 0.0
        ),
    }


def _neutral_audit(schedule: pl.DataFrame) -> dict[str, object]:
    neutral_rows = pl.DataFrame()
    neutral_column = None

    for name in NEUTRAL_COLUMNS:
        if name in schedule.columns:
            neutral_column = name
            series = schedule[name]
            if series.dtype == pl.Boolean:
                neutral_rows = schedule.filter(pl.col(name).fill_null(False))
            else:
                neutral_rows = schedule.filter(
                    pl.col(name)
                    .cast(pl.String, strict=False)
                    .str.to_lowercase()
                    .is_in(["true", "1", "yes", "y"])
                )
            break

    venue_columns = [name for name in VENUE_TEXT_COLUMNS if name in schedule.columns]
    international_rows = pl.DataFrame()

    if venue_columns:
        expr = None
        for column in venue_columns:
            lowered = (
                pl.col(column)
                .cast(pl.String, strict=False)
                .fill_null("")
                .str.to_lowercase()
            )
            column_expr = None
            for term in INTERNATIONAL_TERMS:
                term_expr = lowered.str.contains(term, literal=True)
                column_expr = (
                    term_expr
                    if column_expr is None
                    else column_expr | term_expr
                )
            expr = column_expr if expr is None else expr | column_expr

        if expr is not None:
            international_rows = schedule.filter(expr)

    def rows_to_records(frame: pl.DataFrame) -> list[dict[str, object]]:
        if frame.height == 0:
            return []
        wanted = [
            name
            for name in (
                "game_id",
                "season",
                "week",
                "away_team",
                "home_team",
                *venue_columns,
            )
            if name in frame.columns
        ]
        return frame.select(wanted).to_dicts()

    return {
        "neutral_column": neutral_column,
        "neutral_count": neutral_rows.height,
        "neutral_games": rows_to_records(neutral_rows),
        "venue_text_columns": venue_columns,
        "international_count": international_rows.height,
        "international_games": rows_to_records(international_rows),
    }


def validate_season(
    feature_path: Path,
    schedule_path: Path,
    season: int,
) -> dict[str, object]:
    frame = pl.read_parquet(feature_path)
    schedule = pl.read_parquet(schedule_path)

    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "travel_geography_known",
        *FEATURES,
        *FLAG_FEATURES,
        "travel_rest_known",
        *OPTIONAL_REST_FEATURES,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{feature_path} is missing required columns: "
            + ", ".join(sorted(missing))
        )

    seasons = sorted(frame["season"].drop_nulls().unique().to_list())
    if seasons != [season]:
        raise ValueError(
            f"{feature_path} contains unexpected season values: {seasons}"
        )

    duplicates = frame.height - frame["game_id"].n_unique()
    if duplicates:
        raise ValueError(
            f"{feature_path} contains {duplicates} duplicate game_id rows."
        )

    geo_known = float(frame["travel_geography_known"].mean() or 0.0)
    rest_known = float(frame["travel_rest_known"].mean() or 0.0)

    feature_stats = {
        name: _feature_stats(frame, name)
        for name in FEATURES
    }

    flag_stats = {
        name: {
            "coverage": float(frame[name].is_not_null().mean()),
            "rate": _float(frame[name].mean()),
        }
        for name in FLAG_FEATURES
    }

    rest_stats = {
        name: _feature_stats(frame, name)
        for name in OPTIONAL_REST_FEATURES
        if frame[name].dtype != pl.Boolean
    }
    rest_stats["short_week_away"] = {
        "coverage": float(frame["short_week_away"].is_not_null().mean()),
        "rate": _float(frame["short_week_away"].mean()),
    }

    extremes = (
        frame.filter(pl.col("away_travel_miles").is_not_null())
        .sort("away_travel_miles", descending=True)
        .select(
            "game_id",
            "week",
            "away_team",
            "home_team",
            "away_travel_miles",
            "away_time_zone_shift_hours",
            "cross_country_travel",
            "short_week_away",
        )
        .head(15)
        .to_dicts()
    )

    return {
        "season": season,
        "rows": frame.height,
        "schedule_rows": schedule.height,
        "duplicate_game_ids": duplicates,
        "geography_known_rate": geo_known,
        "rest_known_rate": rest_known,
        "features": feature_stats,
        "flags": flag_stats,
        "rest_features": rest_stats,
        "extreme_trips": extremes,
        "site_audit": _neutral_audit(schedule),
    }


def evaluate(report: dict[str, object]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for season_key, result in report["seasons"].items():
        season = int(season_key)

        if result["rows"] < 250:
            failures.append(f"{season}: fewer than 250 feature rows")

        if result["rows"] != result["schedule_rows"]:
            failures.append(
                f"{season}: feature rows do not match schedule rows"
            )

        if result["geography_known_rate"] < 0.98:
            failures.append(
                f"{season}: geography coverage below 98%"
            )

        miles = result["features"]["away_travel_miles"]
        if miles["std"] is None or miles["std"] < 200:
            failures.append(
                f"{season}: travel-mile dispersion is too low"
            )

        if miles["p95"] is None or miles["p95"] < 1000:
            failures.append(
                f"{season}: travel-mile upper tail is unexpectedly weak"
            )

        timezone = result["features"]["away_time_zone_shift_hours"]
        if timezone["std"] is None or timezone["std"] <= 0:
            failures.append(
                f"{season}: time-zone shift has no dispersion"
            )

        long_haul = result["flags"]["long_haul_travel"]["rate"]
        if long_haul is None or not (0.05 <= long_haul <= 0.60):
            warnings.append(
                f"{season}: long-haul rate is outside expected research band"
            )

        cross_country = result["flags"]["cross_country_travel"]["rate"]
        if cross_country is None or not (0.01 <= cross_country <= 0.35):
            warnings.append(
                f"{season}: cross-country rate is outside expected research band"
            )

        if result["rest_known_rate"] < 0.50:
            warnings.append(
                f"{season}: per-team rest-day coverage is low; "
                "short-week interactions should remain parked"
            )

        audit = result["site_audit"]
        if audit["neutral_count"] or audit["international_count"]:
            warnings.append(
                f"{season}: venue audit found "
                f"{audit['neutral_count']} neutral and "
                f"{audit['international_count']} international-site rows"
            )

    return failures, warnings


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 81B — Travel Fatigue Historical Validation",
        "",
        (
            "This gate validates technical coverage, dispersion, and site-risk "
            "only. It does not claim predictive value."
        ),
        "",
        "## Season health",
        "",
        "| Season | Rows | Geography known | Rest known | Avg miles | P95 miles | Avg TZ shift |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        miles = result["features"]["away_travel_miles"]
        tz = result["features"]["away_time_zone_shift_hours"]
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{result['geography_known_rate']:.1%} | "
            f"{result['rest_known_rate']:.1%} | "
            f"{miles['mean']:.1f} | "
            f"{miles['p95']:.1f} | "
            f"{tz['mean']:.2f} |"
        )

    lines.extend(["", "## Neutral / international-site audit", ""])

    for season, result in report["seasons"].items():
        audit = result["site_audit"]
        lines.append(
            f"- **{season}:** neutral={audit['neutral_count']}, "
            f"international={audit['international_count']}, "
            f"neutral column={audit['neutral_column']!r}"
        )

    lines.extend(["", "## Gate", ""])
    if report["failures"]:
        lines.append("**FAIL**")
        lines.extend(f"- {item}" for item in report["failures"])
    else:
        lines.append(
            "**PASS** — ordinary travel features are technically suitable "
            "for controlled research."
        )

    if report["warnings"]:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])

    lines.extend(
        [
            "",
            (
                "International/neutral-site rows should be excluded or "
                "venue-corrected before wiring travel distance if the audit "
                "identifies material mismatches."
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
        "--feature-dir",
        type=Path,
        default=Path("data/curated/travel_fatigue_features"),
    )
    parser.add_argument(
        "--schedule-dir",
        type=Path,
        default=Path("data/curated/schedules"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    seasons: dict[str, object] = {}
    for season in args.seasons:
        feature_path = (
            args.feature_dir / f"travel_fatigue_features_{season}.parquet"
        )

        schedule_candidates = (
            Path("data/curated/schedules") / f"schedule_{season}.parquet",
            Path("data/curated/schedules") / f"schedules_{season}.parquet",
            Path("data/curated") / "schedules" / f"{season}.parquet",
            Path("data/raw/schedules") / f"schedule_{season}.parquet",
        )
        schedule_path = next(
            (path for path in schedule_candidates if path.exists()),
            None,
        )

        if not feature_path.exists():
            raise FileNotFoundError(
                f"Missing Step 81A artifact for {season}: {feature_path}"
            )
        if schedule_path is None:
            # The schedule path convention is project-specific; recover it from
            # ProjectPaths if available.
            from gridiron.core.paths import ProjectPaths

            candidate = ProjectPaths.from_root(".").schedule_file(season)
            if candidate.exists():
                schedule_path = candidate

        if schedule_path is None:
            raise FileNotFoundError(
                f"Could not locate schedule artifact for {season}"
            )

        seasons[str(season)] = validate_season(
            feature_path,
            schedule_path,
            season,
        )

    report: dict[str, object] = {
        "step": "81B",
        "seasons": seasons,
    }
    failures, warnings = evaluate(report)
    report["failures"] = failures
    report["warnings"] = warnings
    report["status"] = "PASS" if not failures else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "travel_fatigue_validation_81b.json"
    md_path = args.output_dir / "travel_fatigue_validation_81b.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 81B TRAVEL FATIGUE HISTORICAL VALIDATION")
    print("=" * 96)
    for season, result in seasons.items():
        miles = result["features"]["away_travel_miles"]
        audit = result["site_audit"]
        print(
            f"{season}: rows={result['rows']}  "
            f"geo={result['geography_known_rate']:.1%}  "
            f"rest={result['rest_known_rate']:.1%}  "
            f"avg_miles={miles['mean']:.0f}  "
            f"p95={miles['p95']:.0f}  "
            f"neutral={audit['neutral_count']}  "
            f"intl={audit['international_count']}"
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
