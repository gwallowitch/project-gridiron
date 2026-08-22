import importlib.util
import sys
from pathlib import Path

from gridiron.experiments.config import load_experiments

SCRIPT = Path("scripts/validate_step88a_locked_model_integrity.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step88a_locked_model_integrity",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_88a_live_config_is_single_lock() -> None:
    rows = load_experiments(Path("config/experiments.toml"))
    assert len(rows) == 1
    assert rows[0].name == "six_weight_v1_locked"


def test_88a_live_config_passes_integrity() -> None:
    report = MODULE.validate_locked_model(
        Path("config/experiments.toml")
    )

    assert report["status"] == "PASS"
    assert report["failures"] == []


def test_88a_has_exactly_six_active_weights() -> None:
    report = MODULE.validate_locked_model(
        Path("config/experiments.toml")
    )

    assert report["model"]["active_weight_count"] == 6
    assert set(report["model"]["active_weights"]) == set(
        MODULE.LOCKED_WEIGHTS
    )


def test_88a_fingerprint_is_stable() -> None:
    first = MODULE.validate_locked_model(
        Path("config/experiments.toml")
    )
    second = MODULE.validate_locked_model(
        Path("config/experiments.toml")
    )

    assert (
        first["model"]["fingerprint_sha256"]
        == second["model"]["fingerprint_sha256"]
    )
    assert len(first["model"]["fingerprint_sha256"]) == 64
