import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/validate_step82e_environment_robustness.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step82e_environment_robustness",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_82e_robustness_prefers_all_looso_winner() -> None:
    rows = []
    seasons = (2022, 2023, 2024, 2025)
    for season in seasons:
        rows.append(
            {
                "season": season,
                "name": "environment_v1_baseline",
                "selection_score": 0.5000,
            }
        )
        for name, delta in (
            ("adverse_050", -0.0003),
            ("adverse_065", -0.0002),
            ("adverse_075", -0.0001),
            ("high_wind_050", 0.0001),
            ("high_wind_075", 0.0002),
        ):
            rows.append(
                {
                    "season": season,
                    "name": name,
                    "selection_score": 0.5000 + delta,
                }
            )

    report = MODULE.evaluate(rows)

    assert report["candidate"] == "adverse_050"
    assert report["status"] == "PROVISIONAL_PASS"
    assert report["production_eligible"] is False
