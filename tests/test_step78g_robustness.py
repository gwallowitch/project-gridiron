import importlib.util
import sys
from pathlib import Path

path = Path("scripts/validate_step78g_robustness.py")
spec = importlib.util.spec_from_file_location("step78g", path)
assert spec is not None and spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_center_candidate_preferred_when_effectively_tied() -> None:
    stats = {
        "def_epa_trend_050": {
            "mean_score_delta": -0.00121,
            "mean_accuracy_delta": 0.002,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        },
        "def_epa_trend_0525": {
            "mean_score_delta": -0.00115,
            "mean_accuracy_delta": 0.003,
            "looso_improves_count": 4,
            "worst_looso_delta": -0.0001,
        },
        "def_epa_trend_055": {
            "mean_score_delta": -0.00100,
            "mean_accuracy_delta": 0.002,
            "looso_improves_count": 3,
            "worst_looso_delta": 0.0002,
        },
    }

    winner, status = module.choose_candidate(stats)

    assert winner == "def_epa_trend_0525"
    assert status == "PROVISIONAL_PASS"


def test_robustness_gate_holds_unstable_candidate() -> None:
    stats = {
        "def_epa_trend_050": {
            "mean_score_delta": -0.0012,
            "mean_accuracy_delta": 0.002,
            "looso_improves_count": 2,
            "worst_looso_delta": 0.0008,
        },
        "def_epa_trend_0525": {
            "mean_score_delta": -0.0011,
            "mean_accuracy_delta": 0.003,
            "looso_improves_count": 2,
            "worst_looso_delta": 0.0007,
        },
        "def_epa_trend_055": {
            "mean_score_delta": -0.0010,
            "mean_accuracy_delta": 0.002,
            "looso_improves_count": 2,
            "worst_looso_delta": 0.0007,
        },
    }

    _, status = module.choose_candidate(stats)
    assert status == "HOLD"
