"""Local persistence helpers for Project Gridiron datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gridiron.validation.play_by_play import validate_play_by_play
from gridiron.validation.schedules import validate_schedule


def schedule_path(
    season: int,
    root: Path | str = Path("data"),
) -> Path:
    """Return the canonical Parquet path for one NFL schedule season."""
    _validate_season(season)

    return (
        Path(root)
        / "raw"
        / "schedules"
        / f"schedules_{season}.parquet"
    )


def play_by_play_path(
    season: int,
    root: Path | str = Path("data"),
) -> Path:
    """Return the canonical Parquet path for one play-by-play season."""
    _validate_season(season)

    return (
        Path(root)
        / "raw"
        / "play_by_play"
        / f"play_by_play_{season}.parquet"
    )


def persist_schedule(
    frame: Any,
    season: int,
    root: Path | str = Path("data"),
) -> Path:
    """Validate and save one schedule season as compressed Parquet."""
    validate_schedule(frame)

    season_frame = frame.filter(frame["season"] == season)

    if season_frame.height == 0:
        raise ValueError(
            f"Schedule data contains no rows for season {season}."
        )

    output_path = schedule_path(season, root)
    _write_parquet_atomically(season_frame, output_path)

    return output_path


def persist_play_by_play(
    frame: Any,
    season: int,
    root: Path | str = Path("data"),
) -> Path:
    """Validate and save one play-by-play season as compressed Parquet."""
    validate_play_by_play(frame)

    season_frame = frame.filter(frame["season"] == season)

    if season_frame.height == 0:
        raise ValueError(
            f"Play-by-play data contains no rows for season {season}."
        )

    output_path = play_by_play_path(season, root)
    _write_parquet_atomically(season_frame, output_path)

    return output_path


def _write_parquet_atomically(
    frame: Any,
    output_path: Path,
) -> None:
    """Write a Parquet file without leaving partial output behind."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".parquet.tmp")

    try:
        frame.write_parquet(
            temporary_path,
            compression="zstd",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _validate_season(season: int) -> None:
    if season < 1999 or season > 2100:
        raise ValueError(
            "NFL seasons must be between 1999 and 2100."
        )
