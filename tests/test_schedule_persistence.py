from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.data.persistence import persist_schedule, schedule_path


def sample_schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["2025_01_DAL_PHI", "2024_01_BAL_KC"],
            "season": [2025, 2024],
            "week": [1, 1],
            "game_type": ["REG", "REG"],
            "gameday": ["2025-09-04", "2024-09-05"],
            "away_team": ["DAL", "BAL"],
            "home_team": ["PHI", "KC"],
        }
    )


def test_schedule_path_uses_canonical_location(tmp_path: Path) -> None:
    result = schedule_path(2025, tmp_path)

    assert result == (
        tmp_path / "raw" / "schedules" / "schedules_2025.parquet"
    )


def test_schedule_path_rejects_invalid_season(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 1999 and 2100"):
        schedule_path(1998, tmp_path)


def test_persist_schedule_writes_only_requested_season(
    tmp_path: Path,
) -> None:
    output_path = persist_schedule(sample_schedule(), 2025, tmp_path)

    assert output_path.exists()

    saved = pl.read_parquet(output_path)

    assert saved.height == 1
    assert saved["season"].to_list() == [2025]
    assert saved["game_id"].to_list() == ["2025_01_DAL_PHI"]


def test_persist_schedule_rejects_missing_season(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="contains no rows for season 2026",
    ):
        persist_schedule(sample_schedule(), 2026, tmp_path)
