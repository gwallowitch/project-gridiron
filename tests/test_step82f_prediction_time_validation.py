import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from gridiron.weather.contracts import (
    PredictionTimeWeatherSnapshot,
    build_prediction_time_weather_frame,
)

SCRIPT = Path("scripts/validate_step82f_prediction_time_weather.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step82f_prediction_time_weather",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_82f_evaluate_accepts_healthy_snapshot_set() -> None:
    kickoff = datetime(2025, 10, 12, 20, 20, tzinfo=UTC)
    rows = []
    for index in range(10):
        as_of = kickoff - timedelta(hours=3)
        rows.append(
            PredictionTimeWeatherSnapshot(
                game_id=f"g{index}",
                as_of_timestamp=as_of,
                kickoff_timestamp=kickoff,
                forecast_retrieved_at=as_of - timedelta(minutes=15),
                source_id="archive",
                forecast_temperature_f=50.0,
                forecast_wind_mph=10.0,
                forecast_precip_probability=0.25,
            )
        )

    report = MODULE.evaluate(
        build_prediction_time_weather_frame(rows)
    )

    assert report["status"] == "PASS"
    assert report["production_eligible"] is True
