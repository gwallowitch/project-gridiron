import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_play_consistency_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_play_consistency_history",
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
                    "off_success_rate_advantage": {
                        "coverage": 0.944,
                        "std": 0.04,
                    },
                    "def_success_prevention_advantage": {
                        "coverage": 0.944,
                        "std": 0.04,
                    },
                    "success_rate_matchup_advantage": {
                        "coverage": 0.944,
                        "std": 0.06,
                    },
                    "negative_play_matchup_advantage": {
                        "coverage": 0.944,
                        "std": 0.03,
                    },
                },
                "non_finite_counts": {
                    "off_success_rate_advantage": 0,
                    "def_success_prevention_advantage": 0,
                    "success_rate_matchup_advantage": 0,
                    "negative_play_matchup_advantage": 0,
                },
                "out_of_bounds_counts": {
                    "home_off_success_rate": 0,
                    "away_off_success_rate": 0,
                    "home_def_success_prevention_rate": 0,
                    "away_def_success_prevention_rate": 0,
                    "home_off_negative_play_rate": 0,
                    "away_off_negative_play_rate": 0,
                    "home_def_negative_play_forced_rate": 0,
                    "away_def_negative_play_forced_rate": 0,
                },
                "known_feature_mismatch": {
                    "off_success_rate_advantage": 0,
                    "def_success_prevention_advantage": 0,
                    "success_rate_matchup_advantage": 0,
                    "negative_play_matchup_advantage": 0,
                },
            }
        }
    }


def test_87b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())
    assert failures == []
    assert warnings == []


def test_87b_rejects_week1_leakage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week1_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 1" in item for item in failures)


def test_87b_requires_complete_week2plus_history() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week2plus_both_known_rate"] = 0.98

    failures, _ = MODULE.evaluate(report)

    assert any("Week 2+" in item for item in failures)


def test_87b_rejects_zero_dispersion() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["features"][
        "success_rate_matchup_advantage"
    ]["std"] = 0.0

    failures, _ = MODULE.evaluate(report)

    assert any("no dispersion" in item for item in failures)


def test_87b_rejects_known_null_feature() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["known_feature_mismatch"][
        "negative_play_matchup_advantage"
    ] = 1

    failures, _ = MODULE.evaluate(report)

    assert any("missing despite both teams being known" in item for item in failures)
