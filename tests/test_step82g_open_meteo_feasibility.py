import importlib.util
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path("scripts/validate_step82g_open_meteo_feasibility.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step82g_open_meteo_feasibility",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_82g_feasibility_never_marks_production_eligible() -> None:
    frame = pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "kickoff_timestamp": [
                "2025-01-01T20:00:00Z",
                "2025-01-02T20:00:00Z",
            ],
            "forecast_valid_timestamp": [
                "2025-01-01T20:00:00Z",
                "2025-01-02T20:00:00Z",
            ],
            "source_id": ["open-meteo", "open-meteo"],
            "forecast_temperature_f": [40.0, 50.0],
            "forecast_wind_mph": [12.0, 15.0],
            "forecast_precip_probability": [0.2, 0.3],
            "research_only": [True, True],
            "exact_forecast_vintage_known": [False, False],
        }
    )

    report = MODULE.evaluate(frame)

    assert report["status"] == "PASS"
    assert report["production_eligible"] is False
