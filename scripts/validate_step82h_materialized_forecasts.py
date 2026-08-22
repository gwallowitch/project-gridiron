"""Validate materialized 82H Open-Meteo research artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl


def evaluate(frame: pl.DataFrame) -> dict[str, object]:
    required = {
        "game_id",
        "forecast_temperature_f",
        "forecast_wind_mph",
        "forecast_precip_probability",
        "research_only",
        "exact_forecast_vintage_known",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            "82H artifact missing columns: "
            + ", ".join(sorted(missing))
        )

    rows = frame.height
    return {
        "rows": rows,
        "game_id_unique": (
            frame["game_id"].n_unique() == rows
            if rows
            else False
        ),
        "temperature_coverage": (
            float(
                frame["forecast_temperature_f"]
                .is_not_null()
                .mean()
            )
            if rows
            else 0.0
        ),
        "wind_coverage": (
            float(
                frame["forecast_wind_mph"]
                .is_not_null()
                .mean()
            )
            if rows
            else 0.0
        ),
        "precipitation_coverage": (
            float(
                frame["forecast_precip_probability"]
                .is_not_null()
                .mean()
            )
            if rows
            else 0.0
        ),
        "all_research_only": (
            bool(frame["research_only"].all())
            if rows
            else False
        ),
        "any_exact_vintage_known": (
            bool(frame["exact_forecast_vintage_known"].any())
            if rows
            else False
        ),
    }


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
            "data/curated/open_meteo_research_forecasts"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/reports/research/"
            "step82h_materialized_forecasts.json"
        ),
    )
    args = parser.parse_args()

    report = {"step": "82H", "seasons": {}, "production_eligible": False}

    for season in args.seasons:
        path = (
            args.input_dir
            / f"open_meteo_research_forecasts_{season}.parquet"
        )
        if not path.exists():
            raise FileNotFoundError(path)
        report["seasons"][str(season)] = evaluate(
            pl.read_parquet(path)
        )

    report["status"] = "PASS"
    for season, result in report["seasons"].items():
        if (
            not result["game_id_unique"]
            or result["wind_coverage"] < 0.80
            or not result["all_research_only"]
        ):
            report["status"] = "FAIL"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 82H MATERIALIZED FORECAST VALIDATION")
    print("=" * 96)
    for season, result in report["seasons"].items():
        print(
            f"{season}: rows={result['rows']}  "
            f"temp={result['temperature_coverage']:.1%}  "
            f"wind={result['wind_coverage']:.1%}  "
            f"precip={result['precipitation_coverage']:.1%}"
        )
    print("-" * 96)
    print(f"STATUS: {report['status']}")
    print("Production eligible: NO")
    print(f"Report: {args.output.resolve()}")
    print("=" * 96)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
