from datetime import UTC, datetime

from gridiron.weather.open_meteo import (
    build_url,
    fetch_game_snapshot,
)


def test_build_url_requests_required_fields() -> None:
    url = build_url(
        latitude=39.0,
        longitude=-94.0,
        start_date="2025-10-12",
        end_date="2025-10-12",
    )

    assert "historical-forecast-api.open-meteo.com" in url
    assert "temperature_2m" in url
    assert "wind_speed_10m" in url
    assert "precipitation_probability" in url
    assert "timezone=UTC" in url


def test_fetch_game_snapshot_maps_hourly_values() -> None:
    payload = {
        "hourly": {
            "time": [
                "2025-10-12T19:00",
                "2025-10-12T20:00",
                "2025-10-12T21:00",
            ],
            "temperature_2m": [50.0, 48.0, 47.0],
            "wind_speed_10m": [11.0, 14.0, 15.0],
            "precipitation_probability": [10, 35, 50],
            "weather_code": [1, 61, 61],
        }
    }

    frame = fetch_game_snapshot(
        game_id="g1",
        kickoff_timestamp=datetime(
            2025,
            10,
            12,
            20,
            20,
            tzinfo=UTC,
        ),
        latitude=39.0,
        longitude=-94.0,
        fetch_json=lambda _: payload,
    )

    row = frame.row(0, named=True)
    assert row["forecast_temperature_f"] == 48.0
    assert row["forecast_wind_mph"] == 14.0
    assert row["forecast_precip_probability"] == 0.35
    assert row["research_only"] is True
    assert row["exact_forecast_vintage_known"] is False
