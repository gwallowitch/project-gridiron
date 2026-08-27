from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest

from gridiron.market.prospective_integrity import read_chain
from gridiron.market.prospective_operations import initialize_manifest
from gridiron.market.prospective_schedule import (
    EXPECTED_WEEK_COUNTS,
    ProspectiveScheduleError,
    build_retained_schedule,
    retain_schedule,
    validate_retained_file,
    validate_retained_schedule,
)

COUNTS = {1: 2, 2: 1}


def source_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["2026_01_A_B", "2026_01_C_D", "2026_02_A_C", "2026_17_B_D"],
            "season": [2026] * 4,
            "game_type": ["REG"] * 4,
            "week": [1, 1, 2, 17],
            "gameday": ["2026-09-13", "2026-09-13", "2026-09-20", "2026-12-27"],
            "gametime": ["13:00", "20:20", "13:00", "13:00"],
            "away_team": ["A", "C", "A", "B"],
            "home_team": ["B", "D", "C", "D"],
        }
    )


def full_source_frame() -> pl.DataFrame:
    rows = []
    for week, count in EXPECTED_WEEK_COUNTS.items():
        gameday = date(2026, 9, 1) + timedelta(days=7 * (week - 1))
        for index in range(count):
            away = f"A{week:02d}{index:02d}"
            home = f"H{week:02d}{index:02d}"
            rows.append(
                {
                    "game_id": f"2026_{week:02d}_{away}_{home}",
                    "season": 2026,
                    "game_type": "REG",
                    "week": week,
                    "gameday": gameday.isoformat(),
                    "gametime": "13:00",
                    "away_team": away,
                    "home_team": home,
                }
            )
    return pl.DataFrame(rows)


def game_id_digest(rows: list[dict[str, object]]) -> str:
    material = json.dumps(
        sorted(row["game_id"] for row in rows),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(material).hexdigest()


def retained() -> list[dict[str, object]]:
    return build_retained_schedule(
        source_frame(),
        expected_week_counts=COUNTS,
        expected_game_id_digest=None,
    )


def test_adapter_filters_and_normalizes_eastern_kickoffs() -> None:
    rows = retained()
    assert [row["game_id"] for row in rows] == [
        "2026_01_A_B",
        "2026_01_C_D",
        "2026_02_A_C",
    ]
    assert rows[0]["kickoff_at"] == "2026-09-13T17:00:00Z"
    assert rows[1]["kickoff_at"] == "2026-09-14T00:20:00Z"
    assert rows[0]["provider_ids"] == ["2026_01_A_B"]


def test_complete_240_game_contract_passes() -> None:
    rows = build_retained_schedule(full_source_frame(), expected_game_id_digest=None)
    assert len(rows) == 240
    assert {
        week: sum(row["week"] == week for row in rows) for week in range(1, 17)
    } == EXPECTED_WEEK_COUNTS


def test_same_count_wrong_game_fails_exact_universe_digest() -> None:
    expected_digest = game_id_digest(retained())
    changed = source_frame().with_columns(
        pl.when(pl.col("game_id") == "2026_02_A_C")
        .then(pl.lit("2026_02_X_C"))
        .otherwise(pl.col("game_id"))
        .alias("game_id"),
        pl.when(pl.col("game_id") == "2026_02_A_C")
        .then(pl.lit("X"))
        .otherwise(pl.col("away_team"))
        .alias("away_team"),
    )
    with pytest.raises(ProspectiveScheduleError, match="identity universe"):
        build_retained_schedule(
            changed,
            expected_week_counts=COUNTS,
            expected_game_id_digest=expected_digest,
        )


def test_eastern_daylight_and_standard_time_conversion() -> None:
    frame = source_frame().filter(
        pl.col("game_id").is_in(["2026_01_A_B", "2026_02_A_C"])
    )
    frame = frame.with_columns(
        pl.when(pl.col("week") == 2)
        .then(pl.lit("2026-12-20"))
        .otherwise(pl.col("gameday"))
        .alias("gameday")
    )
    rows = build_retained_schedule(
        frame,
        expected_week_counts={1: 1, 2: 1},
        expected_game_id_digest=None,
    )
    assert rows[0]["kickoff_at"] == "2026-09-13T17:00:00Z"
    assert rows[1]["kickoff_at"] == "2026-12-20T18:00:00Z"


def test_retained_serialization_is_deterministic_and_write_once(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    output = tmp_path / "retained.json"
    second_output = tmp_path / "retained-second.json"
    source_frame().write_parquet(source)
    first = retain_schedule(
        source, output, expected_week_counts=COUNTS, enforce_published_contract=False
    )
    second = retain_schedule(
        source, output, expected_week_counts=COUNTS, enforce_published_contract=False
    )
    retain_schedule(
        source,
        second_output,
        expected_week_counts=COUNTS,
        enforce_published_contract=False,
    )
    assert first == second
    assert output.read_bytes().endswith(b"\n")
    assert output.read_bytes() == second_output.read_bytes()


def test_validate_retained_file_matches_source(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    output = tmp_path / "retained.json"
    source_frame().write_parquet(source)
    retain_schedule(
        source, output, expected_week_counts=COUNTS, enforce_published_contract=False
    )
    result = validate_retained_file(
        source,
        output,
        expected_week_counts=COUNTS,
        enforce_published_contract=False,
    )
    assert result["games"] == 3
    assert result["source_sha256"]
    assert result["retained_sha256"]


def test_step91i_initialize_schema_compatibility_is_isolated(tmp_path: Path) -> None:
    schedule_path = tmp_path / "retained.json"
    manifest_path = tmp_path / "test-only-manifest.jsonl"
    schedule_path.write_text(json.dumps(retained()), encoding="utf-8")
    result = initialize_manifest(schedule_path, manifest_path)
    assert result["expected"] == result["added"] == 3
    assert len(read_chain(manifest_path)) == 3


def test_published_source_hash_is_required_by_default(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    source_frame().write_parquet(source)
    with pytest.raises(ProspectiveScheduleError, match="upstream schedule SHA256"):
        retain_schedule(source, tmp_path / "retained.json", expected_week_counts=COUNTS)


@pytest.mark.parametrize(
    ("column", "value", "match"),
    [
        ("season", 2025, "only season 2026"),
        ("game_id", "wrong", "canonical identity"),
        ("gametime", "unknown", "malformed NFLVerse kickoff"),
    ],
)
def test_source_rejections(column: str, value: object, match: str) -> None:
    frame = source_frame().with_columns(pl.lit(value).alias(column))
    with pytest.raises(ProspectiveScheduleError, match=match):
        build_retained_schedule(
            frame, expected_week_counts=COUNTS, expected_game_id_digest=None
        )


def test_missing_game_is_detected() -> None:
    rows = retained()
    expected = {row["game_id"] for row in rows}
    with pytest.raises(ProspectiveScheduleError, match="incomplete"):
        validate_retained_schedule(
            rows[:-1], expected_game_ids=expected, expected_week_counts=COUNTS
        )


def test_duplicate_canonical_and_provider_ids_are_detected() -> None:
    rows = retained()
    duplicate = [*rows, dict(rows[0])]
    counts = {1: 3, 2: 1}
    with pytest.raises(ProspectiveScheduleError, match="duplicate canonical"):
        validate_retained_schedule(
            duplicate,
            expected_game_ids={row["game_id"] for row in rows},
            expected_week_counts=counts,
        )
    rows[1]["provider_ids"] = rows[0]["provider_ids"]
    with pytest.raises(ProspectiveScheduleError, match="duplicate provider"):
        validate_retained_schedule(
            rows,
            expected_game_ids={row["game_id"] for row in rows},
            expected_week_counts=COUNTS,
        )


def test_duplicate_team_date_is_detected() -> None:
    frame = source_frame().with_columns(
        pl.when(pl.col("game_id") == "2026_01_C_D")
        .then(pl.lit("A"))
        .otherwise(pl.col("away_team"))
        .alias("away_team"),
        pl.when(pl.col("game_id") == "2026_01_C_D")
        .then(pl.lit("2026_01_A_D"))
        .otherwise(pl.col("game_id"))
        .alias("game_id"),
    )
    with pytest.raises(ProspectiveScheduleError, match="duplicate team/date"):
        build_retained_schedule(
            frame, expected_week_counts=COUNTS, expected_game_id_digest=None
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("season", 2025, "non-2026"),
        ("season_type", "DIV", "postseason"),
        ("week", 17, "outside 1-16"),
        ("kickoff_at", "not-a-time", "malformed kickoff"),
    ],
)
def test_retained_boundary_rejections(field: str, value: object, match: str) -> None:
    rows = retained()
    rows[0][field] = value
    with pytest.raises(ProspectiveScheduleError, match=match):
        validate_retained_schedule(
            rows,
            expected_game_ids={"2026_01_A_B", "2026_01_C_D", "2026_02_A_C"},
            expected_week_counts=COUNTS,
        )


def test_existing_different_retained_file_is_not_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    output = tmp_path / "retained.json"
    source_frame().write_parquet(source)
    output.write_text("sacred", encoding="utf-8")
    with pytest.raises(ProspectiveScheduleError, match="different content"):
        retain_schedule(
            source,
            output,
            expected_week_counts=COUNTS,
            enforce_published_contract=False,
        )
    assert output.read_text(encoding="utf-8") == "sacred"
