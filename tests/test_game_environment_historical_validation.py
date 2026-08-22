from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_game_environment_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_game_environment_history",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def healthy_report() -> dict[str, object]:
    return {
        "seasons": {
            "2025": {
                "rows": 285,
                "environment_known_rate": 0.95,
                "continuous": {
                    "temperature_f": {
                        "coverage": 0.90,
                        "std": 14.0,
                    },
                    "wind_mph": {
                        "coverage": 0.85,
                        "std": 5.0,
                    },
                },
                "flags": {
                    "adverse_weather": {"rate": 0.15},
                    "indoor_or_closed_roof": {"rate": 0.25},
                },
            }
        }
    }


def test_82b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())

    assert failures == []
    assert warnings == []


def test_82b_rejects_low_environment_coverage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["environment_known_rate"] = 0.50

    failures, _ = MODULE.evaluate(report)

    assert any("environment-known" in item for item in failures)


def test_82b_warns_on_low_wind_coverage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["continuous"]["wind_mph"][
        "coverage"
    ] = 0.40

    _, warnings = MODULE.evaluate(report)

    assert any("wind coverage" in item for item in warnings)


def test_82b_markdown_contains_prediction_time_contract() -> None:
    report = {
        "seasons": {},
        "failures": [],
        "warnings": [],
    }

    text = MODULE.render_markdown(report)

    assert "prediction-time weather contract" in text
    assert "not automatically production-safe" in text
