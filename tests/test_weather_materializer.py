from datetime import UTC, datetime

import polars as pl

from gridiron.weather.materializer import (
    materialize_schedule_forecasts,
)


def test_materializer_builds_rows_and_tracks_skips() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "home_team": ["BUF", "XXX"],
            "kickoff": [
                datetime(
                    2025,
                    10,
                    12,
                    20,
                    20,
                    tzinfo=UTC,
                ),
                datetime(
                    2025,
                    10,
                    12,
                    20,
                    20,
                    tzinfo=UTC,
                ),
            ],
        }
    )

    payload = {
        "hourly": {
            "time": ["2025-10-12T20:00"],
            "temperature_2m": [48.0],
            "wind_speed_10m": [14.0],
            "precipitation_probability": [30],
            "weather_code": [61],
        }
    }

    frame, skipped = materialize_schedule_forecasts(
        schedule,
        fetch_json=lambda _: payload,
    )

    assert frame.height == 1
    assert frame["game_id"].to_list() == ["g1"]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "unknown_home_stadium"
