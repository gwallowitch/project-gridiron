"""Step 88A — locked-model integrity and combined-model validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from gridiron.experiments.config import load_experiments

LOCKED_WEIGHTS = {
    "rest_weight": 0.20,
    "off_sack_weight": 10.0,
    "punt_return_weight": 0.24,
    "long_field_avoidance_weight": 1.0,
    "def_epa_trend_weight": 5.25,
    "defensive_schedule_difficulty_weight": 2.25,
}

PARKED_WEIGHTS = (
    "travel_miles_weight",
    "travel_time_zone_weight",
    "adverse_weather_weight",
    "indoor_environment_weight",
    "high_wind_weight",
    "extreme_cold_weight",
    "forecast_high_wind_weight",
    "pace_play_volume_weight",
    "pace_seconds_weight",
    "tempo_index_weight",
    "performance_stability_weight",
    "recent_margin_weight",
    "close_game_experience_weight",
    "first_half_off_epa_weight",
    "first_half_def_epa_weight",
    "first_half_play_volume_weight",
    "explosive_pass_rate_weight",
    "explosive_rush_rate_weight",
    "explosive_play_rate_weight",
    "off_success_rate_weight",
    "def_success_prevention_weight",
    "success_rate_matchup_weight",
    "negative_play_matchup_weight",
)

EXPECTED_NAME = "six_weight_v1_locked"
EXPECTED_HFA = 1.5
EXPECTED_PROBABILITY_SCALE = 0.14


def _fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_locked_model(
    config_path: Path,
) -> dict[str, object]:
    experiments = load_experiments(config_path)

    failures: list[str] = []
    warnings: list[str] = []

    if len(experiments) != 1:
        failures.append(
            f"Expected exactly one active experiment; found {len(experiments)}."
        )

    if not experiments:
        return {
            "status": "FAIL",
            "failures": failures,
            "warnings": warnings,
            "model": None,
        }

    row = experiments[0]
    payload = asdict(row)

    if row.name != EXPECTED_NAME:
        failures.append(
            f"Expected model name {EXPECTED_NAME!r}; found {row.name!r}."
        )

    if row.home_field_advantage != EXPECTED_HFA:
        failures.append(
            "Home-field advantage changed from locked value "
            f"{EXPECTED_HFA}: {row.home_field_advantage}"
        )

    if row.probability_scale != EXPECTED_PROBABILITY_SCALE:
        failures.append(
            "Probability scale changed from locked value "
            f"{EXPECTED_PROBABILITY_SCALE}: {row.probability_scale}"
        )

    for field, expected in LOCKED_WEIGHTS.items():
        actual = getattr(row, field)
        if actual != expected:
            failures.append(
                f"{field} changed from locked value {expected}: {actual}"
            )

    missing_parked = [
        field for field in PARKED_WEIGHTS
        if not hasattr(row, field)
    ]
    if missing_parked:
        failures.append(
            "Missing parked weight fields: "
            + ", ".join(sorted(missing_parked))
        )

    nonzero_parked = {
        field: getattr(row, field)
        for field in PARKED_WEIGHTS
        if hasattr(row, field) and getattr(row, field) != 0.0
    }
    if nonzero_parked:
        failures.append(
            "Rejected research weights are active: "
            + ", ".join(
                f"{field}={value}"
                for field, value in sorted(nonzero_parked.items())
            )
        )

    active_weights = {
        field: value
        for field, value in payload.items()
        if field.endswith("_weight")
        and isinstance(value, (int, float))
        and value != 0.0
    }

    expected_active = set(LOCKED_WEIGHTS)
    actual_active = set(active_weights)

    extra_active = actual_active.difference(expected_active)
    missing_active = expected_active.difference(actual_active)

    if extra_active:
        failures.append(
            "Unexpected active weights: "
            + ", ".join(sorted(extra_active))
        )

    if missing_active:
        failures.append(
            "Locked active weights missing or zero: "
            + ", ".join(sorted(missing_active))
        )

    lock_payload = {
        "name": row.name,
        "home_field_advantage": row.home_field_advantage,
        "probability_scale": row.probability_scale,
        **LOCKED_WEIGHTS,
        **{
            field: getattr(row, field)
            for field in PARKED_WEIGHTS
            if hasattr(row, field)
        },
    }

    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "model": {
            "name": row.name,
            "home_field_advantage": row.home_field_advantage,
            "probability_scale": row.probability_scale,
            "active_weight_count": len(active_weights),
            "active_weights": active_weights,
            "parked_weight_count": len(PARKED_WEIGHTS),
            "fingerprint_sha256": _fingerprint(lock_payload),
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    model = report.get("model")
    lines = [
        "# Step 88A — Locked Model Integrity",
        "",
        (
            "This gate verifies that feature discovery is closed and the "
            "production research baseline is exactly the intended six-weight "
            "model before combined-model validation begins."
        ),
        "",
    ]

    if model is not None:
        lines.extend(
            [
                "## Locked contract",
                "",
                f"- Model: `{model['name']}`",
                f"- Active weights: {model['active_weight_count']}",
                f"- Parked research weights: {model['parked_weight_count']}",
                f"- Home-field advantage: {model['home_field_advantage']}",
                f"- Probability scale: {model['probability_scale']}",
                f"- SHA-256 fingerprint: `{model['fingerprint_sha256']}`",
                "",
                "### Active weights",
                "",
            ]
        )
        for field, value in sorted(model["active_weights"].items()):
            lines.append(f"- `{field}` = {value}")

    lines.extend(["", "## Gate", ""])

    if report["status"] == "PASS":
        lines.append(
            "**PASS** — the six-weight lock is intact and ready for "
            "combined-model validation."
        )
    else:
        lines.append("**FAIL**")
        lines.extend(f"- {item}" for item in report["failures"])

    if report["warnings"]:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments.toml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    if not args.config.exists():
        raise FileNotFoundError(args.config)

    report = validate_locked_model(args.config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "step88a_locked_model_integrity.json"
    md_path = args.output_dir / "step88a_locked_model_integrity.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 100)
    print("PROJECT GRIDIRON — STEP 88A LOCKED-MODEL INTEGRITY")
    print("=" * 100)

    model = report.get("model")
    if model is not None:
        print(f"Model..................... {model['name']}")
        print(f"Active weights............ {model['active_weight_count']}")
        print(f"Parked research weights... {model['parked_weight_count']}")
        print(f"Home-field advantage...... {model['home_field_advantage']}")
        print(f"Probability scale......... {model['probability_scale']}")
        print(f"Fingerprint............... {model['fingerprint_sha256']}")

    print("-" * 100)
    print(f"STATUS: {report['status']}")

    for warning in report["warnings"]:
        print(f"WARN: {warning}")

    for failure in report["failures"]:
        print(f"FAIL: {failure}")

    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 100)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
