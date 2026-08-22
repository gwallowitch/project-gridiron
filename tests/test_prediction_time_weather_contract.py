from datetime import UTC, datetime, timedelta

import pytest

from gridiron.validation.prediction_time_weather import (
    validate_prediction_time_weather,
)
from gridiron.weather.contracts import (
    PredictionTimeWeatherSnapshot,
    build_prediction_time_weather_frame,
)


def snapshot() -> PredictionTimeWeatherSnapshot:
    kickoff = datetime(2025, 10, 12, 20, 20, tzinfo=UTC)
    as_of = kickoff - timedelta(hours=3)
    return PredictionTimeWeatherSnapshot(
        game_id="2025_06_BUF_KC",
        as_of_timestamp=as_of,
        kickoff_timestamp=kickoff,
        forecast_retrieved_at=as_of - timedelta(minutes=20),
        source_id="historical-forecast-provider",
        forecast_temperature_f=48.0,
        forecast_wind_mph=14.0,
        forecast_precip_probability=0.35,
        forecast_condition="light rain",
        roof_state="outdoor",
    )


def test_prediction_time_snapshot_is_valid() -> None:
    frame = build_prediction_time_weather_frame([snapshot()])
    validate_prediction_time_weather(frame)

    row = frame.row(0, named=True)
    assert row["hours_before_kickoff"] == pytest.approx(3.0)
    assert row["forecast_age_hours"] == pytest.approx(1 / 3)


def test_as_of_after_kickoff_fails() -> None:
    kickoff = datetime(2025, 10, 12, 20, 20, tzinfo=UTC)

    with pytest.raises(ValueError, match="before kickoff"):
        PredictionTimeWeatherSnapshot(
            game_id="g",
            as_of_timestamp=kickoff,
            kickoff_timestamp=kickoff,
            forecast_retrieved_at=kickoff - timedelta(hours=1),
            source_id="source",
        )


def test_future_retrieval_fails() -> None:
    kickoff = datetime(2025, 10, 12, 20, 20, tzinfo=UTC)
    as_of = kickoff - timedelta(hours=3)

    with pytest.raises(ValueError, match="later than as_of"):
        PredictionTimeWeatherSnapshot(
            game_id="g",
            as_of_timestamp=as_of,
            kickoff_timestamp=kickoff,
            forecast_retrieved_at=as_of + timedelta(minutes=1),
            source_id="source",
        )


def test_invalid_precip_probability_fails() -> None:
    kickoff = datetime(2025, 10, 12, 20, 20, tzinfo=UTC)
    as_of = kickoff - timedelta(hours=3)

    with pytest.raises(ValueError, match="between 0 and 1"):
        PredictionTimeWeatherSnapshot(
            game_id="g",
            as_of_timestamp=as_of,
            kickoff_timestamp=kickoff,
            forecast_retrieved_at=as_of,
            source_id="source",
            forecast_precip_probability=1.1,
        )
