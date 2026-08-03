from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.data.persistence import (
    persist_play_by_play,
    play_by_play_path,
)
from gridiron.validation.play_by_play import validate_play_by_play


def sample_play_by_play() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "play_id": [1, 2, 1],
            "game_id": [
                "2025_01_DAL_PHI",
                "2025_01_DAL_PHI",
                "2024_01_BAL_KC",
            ],
            "season": [2025, 2025, 2024],
            "week": [1, 1, 1],
            "posteam": ["DAL", "PHI", "BAL"],
            "defteam": ["PHI", "DAL", "KC"],
        }
    )


def test_validate_play_by_play_accepts_valid_frame() -> None:
    validate_play_by_play(sample_play_by_play())


def test_validate_play_by_play_rejects_missing_columns() -> None:
    frame = pl.DataFrame(
        {
            "play_id": [1],
            "season": [2025],
        }
    )

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        validate_play_by_play(frame)


def test_validate_play_by_play_rejects_empty_frame() -> None:
    frame = sample_play_by_play().head(0)

    with pytest.raises(
        ValueError,
        match="contains no plays",
    ):
        validate_play_by_play(frame)


def test_play_by_play_path_uses_canonical_location(
    tmp_path: Path,
) -> None:
    result = play_by_play_path(2025, tmp_path)

    assert result == (
        tmp_path
        / "raw"
        / "play_by_play"
        / "play_by_play_2025.parquet"
    )


def test_play_by_play_path_rejects_invalid_season(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="between 1999 and 2100",
    ):
        play_by_play_path(1998, tmp_path)


def test_persist_play_by_play_writes_requested_season(
    tmp_path: Path,
) -> None:
    output_path = persist_play_by_play(
        sample_play_by_play(),
        2025,
        tmp_path,
    )

    assert output_path.exists()

    saved = pl.read_parquet(output_path)

    assert saved.height == 2
    assert saved["season"].unique().to_list() == [2025]
    assert saved["game_id"].unique().to_list() == [
        "2025_01_DAL_PHI"
    ]


def test_persist_play_by_play_rejects_missing_season(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="contains no rows for season 2026",
    ):
        persist_play_by_play(
            sample_play_by_play(),
            2026,
            tmp_path,
        )
