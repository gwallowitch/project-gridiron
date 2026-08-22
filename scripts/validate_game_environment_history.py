"""Step 82B historical coverage and leakage validation for game environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

CONTINUOUS = (
    "temperature_f",
    "wind_mph",
)

FLAGS = (
    "indoor_or_closed_roof",
    "retractable_roof",
    "rain_or_precipitation",
    "snow_or_wintry",
    "extreme_cold",
    "extreme_heat",
    "high_wind",
    "adverse_weather",
)

TEXT_COLUMNS = (
    "weather_text",
    "roof_text",
    "surface_text",
    "stadium_text",
)


def _float(value: object) -> float | None:
    return None if value is None else float(value)


def _quantile(series: pl.Series, q: float) -> float | None:
    clean = series.drop_nulls()
    if clean.len() == 0:
        return None
    value = clean.quantile(q, interpolation="linear")
    return None if value is None else float(value)


def _continuous_stats(frame: pl.DataFrame, name: str) -> dict[str, object]:
    series = frame[name]
    clean = series.drop_nulls()
    return {
        "coverage": float(series.is_not_null().mean()),
        "mean": _float(clean.mean()),
        "std": _float(clean.std()),
        "p05": _quantile(clean, 0.05),
        "median": _quantile(clean, 0.50),
        "p95": _quantile(clean, 0.95),
        "min": _float(clean.min()),
        "max": _float(clean.max()),
    }


def _flag_stats(frame: pl.DataFrame, name: str) -> dict[str, object]:
    series = frame[name]
    return {
        "coverage": float(series.is_not_null().mean()),
        "rate": _float(series.mean()),
    }


def validate_season(path: Path, season: int) -> dict[str, object]:
    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "environment_known",
        "adverse_weather_count",
        *CONTINUOUS,
        *FLAGS,
        *TEXT_COLUMNS,
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

    continuous = {
        name: _continuous_stats(frame, name)
        for name in CONTINUOUS
    }
    flags = {
        name: _flag_stats(frame, name)
        for name in FLAGS
    }
    text_coverage = {
        name: float(frame[name].is_not_null().mean())
        for name in TEXT_COLUMNS
    }

    severe = (
        frame.filter(pl.col("adverse_weather_count") >= 2)
        .sort(
            ["adverse_weather_count", "wind_mph"],
            descending=[True, True],
        )
        .select(
            "game_id",
            "week",
            "away_team",
            "home_team",
            "temperature_f",
            "wind_mph",
            "weather_text",
            "roof_text",
            "adverse_weather_count",
        )
        .head(20)
        .to_dicts()
    )

    return {
        "season": season,
        "rows": frame.height,
        "duplicate_game_ids": duplicates,
        "environment_known_rate": float(
            frame["environment_known"].mean() or 0.0
        ),
        "continuous": continuous,
        "flags": flags,
        "text_coverage": text_coverage,
        "severe_environment_games": severe,
    }


def evaluate(report: dict[str, object]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for season_key, result in report["seasons"].items():
        season = int(season_key)

        if result["rows"] < 250:
            failures.append(f"{season}: fewer than 250 game rows")

        if result["environment_known_rate"] < 0.75:
            failures.append(
                f"{season}: environment-known coverage below 75%"
            )

        temp = result["continuous"]["temperature_f"]
        wind = result["continuous"]["wind_mph"]

        if temp["coverage"] < 0.60:
            warnings.append(
                f"{season}: temperature coverage below 60%"
            )
        if wind["coverage"] < 0.50:
            warnings.append(
                f"{season}: wind coverage below 50%"
            )

        if (
            temp["coverage"] >= 0.30
            and (temp["std"] is None or temp["std"] < 5.0)
        ):
            failures.append(
                f"{season}: temperature dispersion is implausibly low"
            )

        if (
            wind["coverage"] >= 0.30
            and (wind["std"] is None or wind["std"] < 1.0)
        ):
            failures.append(
                f"{season}: wind dispersion is implausibly low"
            )

        adverse = result["flags"]["adverse_weather"]["rate"]
        indoor = result["flags"]["indoor_or_closed_roof"]["rate"]

        if adverse is None or adverse > 0.60:
            warnings.append(
                f"{season}: adverse-weather rate is unusually high"
            )
        if indoor is None or indoor > 0.70:
            warnings.append(
                f"{season}: indoor/closed-roof rate is unusually high"
            )

    return failures, warnings


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 82B â€” Game Environment Historical Validation",
        "",
        (
            "This gate validates historical coverage and dispersion only. "
            "It does not claim predictive value."
        ),
        "",
        "## Season health",
        "",
        "| Season | Rows | Environment known | Temp cov | Wind cov | Avg temp | Avg wind | Adverse | Indoor |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for season, result in report["seasons"].items():
        temp = result["continuous"]["temperature_f"]
        wind = result["continuous"]["wind_mph"]
        lines.append(
            f"| {season} | {result['rows']} | "
            f"{result['environment_known_rate']:.1%} | "
            f"{temp['coverage']:.1%} | "
            f"{wind['coverage']:.1%} | "
            f"{temp['mean'] if temp['mean'] is not None else 'NA'} | "
            f"{wind['mean'] if wind['mean'] is not None else 'NA'} | "
            f"{result['flags']['adverse_weather']['rate']:.1%} | "
            f"{result['flags']['indoor_or_closed_roof']['rate']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Leakage / production-use contract",
            "",
            (
                "Observed historical conditions may be used for research "
                "screening, but they are **not automatically production-safe**."
            ),
            "",
            (
                "Any Step 82C+ experiment that survives historical screening "
                "must later be revalidated against a prediction-time weather "
                "contract using only information available before the model's "
                "decision timestamp."
            ),
            "",
            (
                "Production promotion must not depend on exact postgame-observed "
                "weather fields."
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
            "**PASS** â€” the historical environment family is technically "
            "researchable."
        )

    if report["warnings"]:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])

    lines.append("")
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
        default=Path("data/curated/game_environment_features"),
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
            / f"game_environment_features_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Step 82A artifact for {season}: {path}"
            )
        seasons[str(season)] = validate_season(path, season)

    report: dict[str, object] = {
        "step": "82B",
        "seasons": seasons,
        "prediction_time_contract": {
            "historical_observed_weather_allowed_for_research": True,
            "historical_observed_weather_allowed_for_direct_production_promotion": False,
            "future_requirement": (
                "Use only weather data available before the model decision timestamp."
            ),
        },
    }

    failures, warnings = evaluate(report)
    report["failures"] = failures
    report["warnings"] = warnings
    report["status"] = "PASS" if not failures else "FAIL"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = (
        args.output_dir
        / "game_environment_validation_82b.json"
    )
    md_path = (
        args.output_dir
        / "game_environment_validation_82b.md"
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
    print(
        "PROJECT GRIDIRON â€” STEP 82B "
        "GAME ENVIRONMENT HISTORICAL VALIDATION"
    )
    print("=" * 96)

    for season, result in seasons.items():
        temp = result["continuous"]["temperature_f"]
        wind = result["continuous"]["wind_mph"]
        print(
            f"{season}: rows={result['rows']}  "
            f"known={result['environment_known_rate']:.1%}  "
            f"temp={temp['coverage']:.1%}  "
            f"wind={wind['coverage']:.1%}  "
            f"adverse="
            f"{result['flags']['adverse_weather']['rate']:.1%}"
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

