import importlib.util
import sys
from pathlib import Path

PATH = Path("scripts/validate_step79e_robustness.py")
SPEC = importlib.util.spec_from_file_location("step79e_robustness", PATH)
assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_choose_candidate_passes_stable_improver() -> None:
    stats = {
        "def_sos_150": {
            "mean_score_delta": -0.00015,
            "mean_accuracy_delta": -0.001,
            "looso_improves_count": 3,
            "worst_looso_delta": 0.0001,
        },
        "def_sos_200": {
            "mean_score_delta": -0.00035,
            "mean_accuracy_delta": -0.001,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        },
        "def_sos_225": {
            "mean_score_delta": -0.00039,
            "mean_accuracy_delta": -0.001,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        },
        "def_sos_250": {
            "mean_score_delta": -0.00040,
            "mean_accuracy_delta": -0.001,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        },
        "def_sos_275": {
            "mean_score_delta": -0.00038,
            "mean_accuracy_delta": -0.002,
            "looso_improves_count": 3,
            "worst_looso_delta": 0.0002,
        },
    }

    winner, status = MODULE.choose_candidate(stats)

    assert winner == "def_sos_225"
    assert status == "PROVISIONAL_PASS"


def test_choose_candidate_holds_accuracy_degradation() -> None:
    stats = {
        name: {
            "mean_score_delta": -0.0004,
            "mean_accuracy_delta": -0.004,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        }
        for name in MODULE.CANDIDATES
    }

    _, status = MODULE.choose_candidate(stats)

    assert status == "HOLD"
