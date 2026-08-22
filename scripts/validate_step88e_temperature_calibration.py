"""Validate the frozen Step 88E temperature calibration contract."""

from __future__ import annotations

import argparse
import json
from itertools import pairwise
from pathlib import Path

from gridiron.calibration.temperature import (
    calibrate_probability,
    load_temperature_contract,
)

EXPECTED_FINGERPRINT = (
    "b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(
            "config/temperature_calibration_v1.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    contract = load_temperature_contract(
        args.contract
    )
    failures: list[str] = []

    if (
        contract.source_fingerprint_sha256
        != EXPECTED_FINGERPRINT
    ):
        failures.append(
            "Calibration contract fingerprint does not match the locked model."
        )

    if contract.training_seasons != (
        2022,
        2023,
        2024,
        2025,
    ):
        failures.append(
            "Calibration contract training seasons changed."
        )

    probes = (
        0.01,
        0.10,
        0.25,
        0.49,
        0.50,
        0.51,
        0.75,
        0.90,
        0.99,
    )

    outputs = {
        value: calibrate_probability(
            value,
            slope=contract.slope,
        )
        for value in probes
    }

    if outputs[0.50] != 0.50:
        failures.append(
            "Temperature scaling moved the 0.5 winner boundary."
        )

    for raw, calibrated in outputs.items():
        if (raw >= 0.5) != (calibrated >= 0.5):
            failures.append(
                f"Winner-side flip detected for raw probability {raw}."
            )

        if calibrated < 0.0 or calibrated > 1.0:
            failures.append(
                f"Calibrated probability outside [0, 1] for {raw}."
            )

    monotonic = all(
        outputs[a] < outputs[b]
        for a, b in pairwise(probes)
    )
    if not monotonic:
        failures.append(
            "Temperature calibration is not strictly monotonic."
        )

    report = {
        "step": "88E",
        "status": (
            "PASS"
            if not failures
            else "FAIL"
        ),
        "contract": {
            "method": contract.method,
            "slope": contract.slope,
            "intercept": contract.intercept,
            "source_step": contract.source_step,
            "source_fingerprint_sha256": (
                contract.source_fingerprint_sha256
            ),
            "training_seasons": list(
                contract.training_seasons
            ),
            "population_games": (
                contract.population_games
            ),
        },
        "probe_outputs": {
            str(raw): calibrated
            for raw, calibrated in outputs.items()
        },
        "failures": failures,
    }

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    output = (
        args.output_dir
        / "step88e_temperature_calibration_validation.json"
    )
    output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("=" * 104)
    print(
        "PROJECT GRIDIRON â€” STEP 88E TEMPERATURE CALIBRATION VALIDATION"
    )
    print("=" * 104)
    print(
        f"Method.................... {contract.method}"
    )
    print(
        f"Slope..................... {contract.slope:.8f}"
    )
    print(
        f"Population games.......... {contract.population_games}"
    )
    print(
        "Winner boundary............ "
        f"{'PRESERVED' if outputs[0.5] == 0.5 else 'FAILED'}"
    )
    print(
        "Monotonic.................. "
        f"{'YES' if monotonic else 'NO'}"
    )
    print("-" * 104)
    print(
        f"STATUS: {report['status']}"
    )

    for failure in failures:
        print(f"FAIL: {failure}")

    print(
        f"Report: {output.resolve()}"
    )
    print("=" * 104)

    return (
        0
        if report["status"] == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

