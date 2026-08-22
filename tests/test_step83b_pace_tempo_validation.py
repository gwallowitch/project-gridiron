import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_pace_tempo_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_pace_tempo_history",
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
                    "pace_play_volume_advantage": {
                        "coverage": 0.944,
                        "std": 4.0,
                    },
                    "pace_seconds_advantage": {
                        "coverage": 0.944,
                        "std": 3.0,
                    },
                    "tempo_index_advantage": {
                        "coverage": 0.944,
                        "std": 0.2,
                    },
                },
                "non_finite_counts": {
                    "pace_play_volume_advantage": 0,
                    "pace_seconds_advantage": 0,
                    "tempo_index_advantage": 0,
                },
            }
        }
    }


def test_83b_accepts_healthy_report() -> None:
    failures, warnings = MODULE.evaluate(healthy_report())

    assert failures == []
    assert warnings == []


def test_83b_rejects_week1_leakage() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["week1_all_unknown"] = False

    failures, _ = MODULE.evaluate(report)

    assert any("Week 1" in item for item in failures)


def test_83b_rejects_zero_dispersion() -> None:
    report = healthy_report()
    report["seasons"]["2025"]["features"][
        "tempo_index_advantage"
    ]["std"] = 0.0

    failures, _ = MODULE.evaluate(report)

    assert any("no dispersion" in item for item in failures)


def test_83b_markdown_mentions_leakage_contract() -> None:
    report = {
        "seasons": {},
        "failures": [],
        "warnings": [],
    }

    text = MODULE.render_markdown(report)

    assert "Leakage contract" in text
    assert "Current-game pace observations" in text
