"""Materialize schedule-aligned Open-Meteo research forecast artifacts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from gridiron.weather.open_meteo import (
    combine_snapshots,
    fetch_game_snapshot,
)
from gridiron.weather.stadiums import stadium_for_team

KICKOFF_COLUMNS = (
    "gameday",
    "game_date",
    "kickoff",
    "kickoff_time",
    "datetime",
    "game_datetime",
)


def _kickoff_column(schedule: pl.DataFrame) -> str:
    for name in KICKOFF_COLUMNS:
        if name in schedule.columns:
            return name
    raise ValueError(
        "Schedule does not contain a supported kickoff datetime column."
    )


def _parse_kickoff(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)


def materialize_schedule_forecasts(
    schedule: pl.DataFrame,
    *,
    fetch_json: Callable[[str], dict],
) -> tuple[pl.DataFrame, list[dict[str, object]]]:
    """Fetch one stitched historical-forecast row per schedule game."""
    required = {"game_id", "home_team"}
    missing = required.difference(schedule.columns)
    if missing:
        raise ValueError(
            "Schedule is missing required columns: "
            + ", ".join(sorted(missing))
        )

    kickoff_column = _kickoff_column(schedule)
    frames: list[pl.DataFrame] = []
    skipped: list[dict[str, object]] = []

    for row in schedule.iter_rows(named=True):
        location = stadium_for_team(str(row["home_team"]))
        if location is None:
            skipped.append(
                {
                    "game_id": row["game_id"],
                    "reason": "unknown_home_stadium",
                    "home_team": row["home_team"],
                }
            )
            continue

        try:
            kickoff = _parse_kickoff(row[kickoff_column])
        except (TypeError, ValueError) as exc:
            skipped.append(
                {
                    "game_id": row["game_id"],
                    "reason": "invalid_kickoff",
                    "detail": str(exc),
                }
            )
            continue

        frames.append(
            fetch_game_snapshot(
                game_id=str(row["game_id"]),
                kickoff_timestamp=kickoff,
                latitude=location.latitude,
                longitude=location.longitude,
                fetch_json=fetch_json,
            )
        )

    return combine_snapshots(frames), skipped


def write_materialized_artifacts(
    *,
    season: int,
    frame: pl.DataFrame,
    skipped: list[dict[str, object]],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = (
        output_dir
        / f"open_meteo_research_forecasts_{season}.parquet"
    )
    skipped_path = (
        output_dir
        / f"open_meteo_research_forecasts_{season}.skipped.json"
    )

    frame.write_parquet(parquet_path)

    import json

    skipped_path.write_text(
        json.dumps(skipped, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return parquet_path, skipped_path

