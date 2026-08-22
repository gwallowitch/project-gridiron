import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_performance_stability_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_performance_stability_history",
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
                "week2_margin_known_rate": 1.0,
                "week2_stability_all_unknown": True,
                "week3plus_stability_known_rate": 1.0,
                "features": {
                    "stability_advantage": {
                        "coverage": 0.888,
                        "std": 4.0,
                    },
                    "recent_margin_advantage": {
                        "coverage": 0.944,
                        "std": 7.0,
                    },
                    "close_game_experience_advantage": {
                        "coverage": 0.944,
                        "std": 0.3,
                    },
                },
                "non_finite_counts": {
                    "stability_advantage": 0,
                    "recent_margin_advantage": 0,
                    "close_game_experience_advantage": 0,
                },
            }
        }
    }


def test_84b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())
    assert failures == []
    assert warnings == []


def test_84b_rejects_week1_leakage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week1_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 1" in item for item in failures)


def test_84b_requires_week2_stability_unknown() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week2_stability_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 2 stability" in item for item in failures)


def test_84b_rejects_zero_dispersion() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["features"][
        "stability_advantage"
    ]["std"] = 0.0

    failures, _ = MODULE.evaluate(report)

    assert any("no dispersion" in item for item in failures)


def test_84b_markdown_mentions_leakage_contract() -> None:
    report = {
        "seasons": {},
        "failures": [],
        "warnings": [],
    }

    text = MODULE.render_markdown(report)

    assert "Leakage contract" in text
    assert "Current-game scores" in text
