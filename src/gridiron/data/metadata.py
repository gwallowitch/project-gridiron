"""DuckDB metadata catalog for Project Gridiron ingestion runs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb

PIPELINE_VERSION = "0.3.0"

_CREATE_INGESTION_LOG = """
CREATE TABLE IF NOT EXISTS ingestion_log (
    run_id VARCHAR PRIMARY KEY,
    dataset VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    row_count BIGINT NOT NULL,
    column_count INTEGER NOT NULL,
    file_path VARCHAR NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    imported_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    pipeline_version VARCHAR NOT NULL,
    error_message VARCHAR
)
"""


def initialize_catalog(database_path: Path | str) -> Path:
    """Create the DuckDB catalog and ingestion table when needed."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(path)) as connection:
        connection.execute(_CREATE_INGESTION_LOG)

    return path


def record_ingestion(
    *,
    database_path: Path | str,
    dataset: str,
    season: int,
    row_count: int,
    column_count: int,
    file_path: Path | str,
    file_size_bytes: int,
    status: str = "success",
    pipeline_version: str = PIPELINE_VERSION,
    error_message: str | None = None,
) -> str:
    """Record one completed or failed dataset-ingestion attempt."""
    _validate_record(
        dataset=dataset,
        season=season,
        row_count=row_count,
        column_count=column_count,
        file_size_bytes=file_size_bytes,
        status=status,
    )

    catalog_path = initialize_catalog(database_path)
    run_id = str(uuid4())
    imported_at = datetime.now(UTC).replace(tzinfo=None)

    with duckdb.connect(str(catalog_path)) as connection:
        connection.execute(
            """
            INSERT INTO ingestion_log (
                run_id,
                dataset,
                season,
                row_count,
                column_count,
                file_path,
                file_size_bytes,
                imported_at,
                status,
                pipeline_version,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                dataset,
                season,
                row_count,
                column_count,
                str(Path(file_path)),
                file_size_bytes,
                imported_at,
                status,
                pipeline_version,
                error_message,
            ],
        )

    return run_id


def read_ingestion_log(
    database_path: Path | str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return recent ingestion records in reverse chronological order."""
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    catalog_path = initialize_catalog(database_path)

    with duckdb.connect(str(catalog_path)) as connection:
        cursor = connection.execute(
            """
            SELECT
                run_id,
                dataset,
                season,
                row_count,
                column_count,
                file_path,
                file_size_bytes,
                imported_at,
                status,
                pipeline_version,
                error_message
            FROM ingestion_log
            ORDER BY imported_at DESC
            LIMIT ?
            """,
            [limit],
        )
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(columns, row, strict=True)) for row in rows]


def _validate_record(
    *,
    dataset: str,
    season: int,
    row_count: int,
    column_count: int,
    file_size_bytes: int,
    status: str,
) -> None:
    if not dataset.strip():
        raise ValueError("Dataset name cannot be empty.")

    if season < 1999 or season > 2100:
        raise ValueError("NFL seasons must be between 1999 and 2100.")

    if row_count < 0:
        raise ValueError("Row count cannot be negative.")

    if column_count < 0:
        raise ValueError("Column count cannot be negative.")

    if file_size_bytes < 0:
        raise ValueError("File size cannot be negative.")

    if status not in {"success", "failed"}:
        raise ValueError("Status must be either 'success' or 'failed'.")
