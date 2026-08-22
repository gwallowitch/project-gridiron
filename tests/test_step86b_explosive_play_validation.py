import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_explosive_play_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_explosive_play_history",
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
                "duplicate_game_ids": 0,
                "week1_all_unknown": True,
                "week2plus_both_known_rate": 1.0,
                "features": {
                    "explosive_pass_rate_advantage": {
                        "coverage": 0.944,
                        "std": 0.05,
                    },
                    "explosive_rush_rate_advantage": {
                        "coverage": 0.944,
                        "std": 0.05,
                    },
                    "explosive_play_rate_advantage": {
                        "coverage": 0.944,
                        "std": 0.04,
                    },
                },
                "non_finite_counts": {
                    "explosive_pass_rate_advantage": 0,
                    "explosive_rush_rate_advantage": 0,
                    "explosive_play_rate_advantage": 0,
                },
                "out_of_bounds_counts": {
                    "home_explosive_pass_rate": 0,
                    "away_explosive_pass_rate": 0,
                    "home_explosive_rush_rate": 0,
                    "away_explosive_rush_rate": 0,
                    "home_explosive_play_rate": 0,
                    "away_explosive_play_rate": 0,
                },
            }
        }
    }


def test_86b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())
    assert failures == []
    assert warnings == []


def test_86b_rejects_week1_leakage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week1_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 1" in item for item in failures)


def test_86b_rejects_zero_dispersion() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["features"][
        "explosive_play_rate_advantage"
    ]["std"] = 0.0

    failures, _ = MODULE.evaluate(report)

    assert any("no dispersion" in item for item in failures)


def test_86b_rejects_non_finite_values() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["non_finite_counts"][
        "explosive_rush_rate_advantage"
    ] = 1

    failures, _ = MODULE.evaluate(report)

    assert any("non-finite" in item for item in failures)


def test_86b_rejects_out_of_bounds_rates() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["out_of_bounds_counts"][
        "home_explosive_pass_rate"
    ] = 1

    failures, _ = MODULE.evaluate(report)

    assert any("outside [0, 1]" in item for item in failures)
