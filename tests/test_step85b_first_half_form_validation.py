import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_first_half_form_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_first_half_form_history",
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
                    "first_half_off_epa_advantage": {
                        "coverage": 0.944,
                        "std": 0.1,
                    },
                    "first_half_def_epa_advantage": {
                        "coverage": 0.944,
                        "std": 0.1,
                    },
                    "first_half_play_volume_advantage": {
                        "coverage": 0.944,
                        "std": 3.0,
                    },
                },
                "non_finite_counts": {
                    "first_half_off_epa_advantage": 0,
                    "first_half_def_epa_advantage": 0,
                    "first_half_play_volume_advantage": 0,
                },
            }
        }
    }


def test_85b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())
    assert failures == []
    assert warnings == []


def test_85b_rejects_week1_leakage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week1_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 1" in item for item in failures)


def test_85b_rejects_zero_dispersion() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["features"][
        "first_half_off_epa_advantage"
    ]["std"] = 0.0

    failures, _ = MODULE.evaluate(report)

    assert any("no dispersion" in item for item in failures)


def test_85b_rejects_non_finite_values() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["non_finite_counts"][
        "first_half_def_epa_advantage"
    ] = 1

    failures, _ = MODULE.evaluate(report)

    assert any("non-finite" in item for item in failures)


def test_85b_markdown_mentions_leakage_contract() -> None:
    report = {
        "seasons": {},
        "failures": [],
        "warnings": [],
    }

    text = MODULE.render_markdown(report)

    assert "Leakage contract" in text
    assert "Current-game first-half plays" in text
