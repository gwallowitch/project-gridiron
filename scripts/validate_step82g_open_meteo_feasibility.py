"""Validate an Open-Meteo stitched historical-forecast research artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

REQUIRED = {
    "game_id",
    "kickoff_timestamp",
    "forecast_valid_timestamp",
    "source_id",
    "forecast_temperature_f",
    "forecast_wind_mph",
    "forecast_precip_probability",
    "research_only",
    "exact_forecast_vintage_known",
}


def evaluate(frame: pl.DataFrame) -> dict[str, object]:
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Missing Open-Meteo feasibility columns: "
            + ", ".join(sorted(missing))
        )

    rows = frame.height
    temp_cov = (
        float(frame["forecast_temperature_f"].is_not_null().mean())
        if rows
        else 0.0
    )
    wind_cov = (
        float(frame["forecast_wind_mph"].is_not_null().mean())
        if rows
        else 0.0
    )
    precip_cov = (
        float(
            frame["forecast_precip_probability"]
            .is_not_null()
            .mean()
        )
        if rows
        else 0.0
    )

    all_research_only = (
        bool(frame["research_only"].all())
        if rows
        else False
    )
    any_exact_vintage = (
        bool(frame["exact_forecast_vintage_known"].any())
        if rows
        else False
    )

    status = "PASS" if rows and wind_cov >= 0.80 else "FAIL"

    return {
        "step": "82G",
        "rows": rows,
        "temperature_coverage": temp_cov,
        "wind_coverage": wind_cov,
        "precipitation_probability_coverage": precip_cov,
        "all_rows_research_only": all_research_only,
        "any_exact_forecast_vintage_known": any_exact_vintage,
        "status": status,
        "production_eligible": False,
        "reason": (
            "Open-Meteo Historical Forecast is a stitched forecast series; "
            "exact historical 2–4 hour pre-kickoff issuance time is not "
            "preserved for the full 2022–2025 study window."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/reports/research/"
            "step82g_open_meteo_feasibility.json"
        ),
    )
    args = parser.parse_args()

    if not args.artifact.exists():
        raise FileNotFoundError(args.artifact)

    report = evaluate(pl.read_parquet(args.artifact))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 82G OPEN-METEO FEASIBILITY")
    print("=" * 96)
    print(f"Rows...................... {report['rows']}")
    print(
        "Temperature coverage...... "
        f"{report['temperature_coverage']:.1%}"
    )
    print(f"Wind coverage............. {report['wind_coverage']:.1%}")
    print(
        "Precip probability........ "
        f"{report['precipitation_probability_coverage']:.1%}"
    )
    print(f"Status.................... {report['status']}")
    print("Production eligible....... NO")
    print(f"Reason.................... {report['reason']}")
    print(f"Report: {args.output.resolve()}")
    print("=" * 96)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
