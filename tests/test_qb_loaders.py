from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.features.qb.loaders import (
    load_qb_ratings,
    load_qb_starters,
)


def test_missing_files_return_empty_frames(
    tmp_path: Path,
) -> None:
    assert load_qb_ratings(tmp_path / "missing.csv").height == 0
    assert load_qb_starters(tmp_path / "missing.csv").height == 0


def test_loads_valid_qb_ratings(tmp_path: Path) -> None:
    path = tmp_path / "ratings.csv"
    path.write_text(
        "qb_name,rating\nStarter A,4.5\n",
        encoding="utf-8",
    )

    frame = load_qb_ratings(path)

    assert frame.row(0, named=True) == {
        "qb_name": "Starter A",
        "rating": 4.5,
    }


def test_duplicate_ratings_are_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ratings.csv"
    path.write_text(
        "qb_name,rating\nStarter A,4.5\nStarter A,3.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_qb_ratings(path)


def test_duplicate_starters_are_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "starters.csv"
    path.write_text(
        (
            "season,week,team,qb_name\n"
            "2025,1,AAA,Starter A\n"
            "2025,1,AAA,Starter B\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_qb_starters(path)
