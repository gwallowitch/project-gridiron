from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.data.metadata import (
    initialize_catalog,
    read_ingestion_log,
    record_ingestion,
)


def test_initialize_catalog_creates_database(tmp_path: Path) -> None:
    database_path = tmp_path / "database" / "gridiron.duckdb"

    result = initialize_catalog(database_path)

    assert result == database_path
    assert database_path.exists()


def test_record_ingestion_writes_metadata(tmp_path: Path) -> None:
    database_path = tmp_path / "gridiron.duckdb"
    parquet_path = tmp_path / "schedules_2025.parquet"
    parquet_path.write_bytes(b"test parquet content")

    run_id = record_ingestion(
        database_path=database_path,
        dataset="schedules",
        season=2025,
        row_count=285,
        column_count=46,
        file_path=parquet_path,
        file_size_bytes=parquet_path.stat().st_size,
    )

    records = read_ingestion_log(database_path)

    assert len(records) == 1
    assert records[0]["run_id"] == run_id
    assert records[0]["dataset"] == "schedules"
    assert records[0]["season"] == 2025
    assert records[0]["row_count"] == 285
    assert records[0]["column_count"] == 46
    assert records[0]["status"] == "success"
    assert records[0]["pipeline_version"] == "0.3.0"


def test_read_ingestion_log_returns_newest_first(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gridiron.duckdb"

    record_ingestion(
        database_path=database_path,
        dataset="schedules",
        season=2024,
        row_count=285,
        column_count=46,
        file_path="schedules_2024.parquet",
        file_size_bytes=100,
    )
    record_ingestion(
        database_path=database_path,
        dataset="schedules",
        season=2025,
        row_count=285,
        column_count=46,
        file_path="schedules_2025.parquet",
        file_size_bytes=110,
    )

    records = read_ingestion_log(database_path)

    assert len(records) == 2
    assert records[0]["season"] == 2025
    assert records[1]["season"] == 2024


def test_record_ingestion_rejects_invalid_status(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="either 'success' or 'failed'",
    ):
        record_ingestion(
            database_path=tmp_path / "gridiron.duckdb",
            dataset="schedules",
            season=2025,
            row_count=285,
            column_count=46,
            file_path="schedule.parquet",
            file_size_bytes=100,
            status="pending",
        )


def test_read_ingestion_log_rejects_invalid_limit(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        read_ingestion_log(
            tmp_path / "gridiron.duckdb",
            limit=0,
        )
