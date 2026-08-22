"""Step 82F feasibility gate for prediction-time weather snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from gridiron.validation.prediction_time_weather import (
    validate_prediction_time_weather,
)


def evaluate(frame: pl.DataFrame) -> dict[str, object]:
    validate_prediction_time_weather(frame)

    rows = frame.height
    missing_rate = (
        float(frame["is_missing"].mean() or 0.0)
        if rows
        else 1.0
    )

    usable = frame.filter(~pl.col("is_missing"))
    temp_cov = (
        float(usable["forecast_temperature_f"].is_not_null().mean())
        if usable.height
        else 0.0
    )
    wind_cov = (
        float(usable["forecast_wind_mph"].is_not_null().mean())
        if usable.height
        else 0.0
    )

    freshness_p95 = (
        usable["forecast_age_hours"].quantile(0.95)
        if usable.height
        else None
    )
    lead_median = (
        usable["hours_before_kickoff"].median()
        if usable.height
        else None
    )

    failures = []
    warnings = []

    if rows == 0:
        failures.append("No prediction-time weather snapshots were supplied.")
    if missing_rate > 0.20:
        warnings.append("More than 20% of snapshots are marked missing.")
    if temp_cov < 0.80:
        warnings.append("Forecast temperature coverage is below 80%.")
    if wind_cov < 0.80:
        warnings.append("Forecast wind coverage is below 80%.")
    if freshness_p95 is not None and freshness_p95 > 24.0:
        warnings.append("95th-percentile forecast age exceeds 24 hours.")
    if lead_median is not None and lead_median < 1.0:
        warnings.append(
            "Median snapshot lead time is under one hour before kickoff."
        )

    status = "PASS" if not failures else "FAIL"

    return {
        "step": "82F",
        "rows": rows,
        "missing_rate": missing_rate,
        "temperature_coverage": temp_cov,
        "wind_coverage": wind_cov,
        "forecast_age_p95_hours": (
            None if freshness_p95 is None else float(freshness_p95)
        ),
        "median_hours_before_kickoff": (
            None if lead_median is None else float(lead_median)
        ),
        "status": status,
        "warnings": warnings,
        "failures": failures,
        "production_eligible": (
            status == "PASS"
            and not warnings
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "snapshot_file",
        type=Path,
        help="Parquet file containing prediction-time weather snapshots.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/reports/research/"
            "step82f_prediction_time_weather_validation.json"
        ),
    )
    args = parser.parse_args()

    if not args.snapshot_file.exists():
        raise FileNotFoundError(args.snapshot_file)

    frame = pl.read_parquet(args.snapshot_file)
    report = evaluate(frame)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 82F PREDICTION-TIME WEATHER VALIDATION")
    print("=" * 96)
    print(f"Rows...................... {report['rows']}")
    print(f"Missing rate.............. {report['missing_rate']:.1%}")
    print(f"Temperature coverage...... {report['temperature_coverage']:.1%}")
    print(f"Wind coverage............. {report['wind_coverage']:.1%}")
    print(f"Status.................... {report['status']}")
    print(f"Production eligible....... {report['production_eligible']}")
    for item in report["warnings"]:
        print(f"WARN: {item}")
    for item in report["failures"]:
        print(f"FAIL: {item}")
    print(f"Report: {args.output.resolve()}")
    print("=" * 96)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
