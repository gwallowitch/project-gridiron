from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from gridiron.market.collection_attempts import (
    CollectionAttemptError,
    append_collection_attempt,
    build_collection_attempt,
    read_collection_attempts,
)
from gridiron.market.operational_history import canonical_json

NOW = datetime(2026, 9, 13, 5, 0, tzinfo=UTC)
KICKOFF = "2026-09-13T17:00:00Z"


def attempt() -> dict[str, object]:
    return build_collection_attempt(
        game_id="2026_01_ATL_PIT",
        collection_target="T12H",
        target_minutes_to_kickoff=720,
        kickoff_at=KICKOFF,
        attempted_at=NOW,
        result="FAILED",
        reason_code="ODDS_PROVIDER_ERROR",
    )


def rehash(record: dict[str, object]) -> dict[str, object]:
    updated = deepcopy(record)
    updated.pop("attempt_id", None)
    updated["attempt_id"] = hashlib.sha256(
        canonical_json(updated).encode("utf-8")
    ).hexdigest()
    return updated


def test_valid_attempt_append_and_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    record = attempt()
    append_collection_attempt(path, record)
    assert read_collection_attempts(path) == (record,)


@pytest.mark.parametrize(
    "mutation",
    ["extra", "credential", "missing_identity", "forged_identity", "semantic"],
)
def test_invalid_new_record_is_rejected_before_existing_bytes_change(
    tmp_path: Path, mutation: str
) -> None:
    path = tmp_path / "attempts.jsonl"
    existing = attempt()
    append_collection_attempt(path, existing)
    before = path.read_bytes()
    invalid = build_collection_attempt(
        game_id="2026_01_BAL_IND",
        collection_target="T12H",
        target_minutes_to_kickoff=720,
        kickoff_at=KICKOFF,
        attempted_at=NOW,
        result="FAILED",
        reason_code="ODDS_PROVIDER_ERROR",
    )
    if mutation == "extra":
        invalid["unexpected"] = "value"
    elif mutation == "credential":
        invalid["api_key"] = "SHOULD_NOT_BE_WRITTEN"
    elif mutation == "missing_identity":
        invalid.pop("attempt_id")
    elif mutation == "forged_identity":
        invalid["attempt_id"] = "0" * 64
    else:
        invalid["reason_code"] = "SUCCESS"
        invalid = rehash(invalid)
    with pytest.raises(CollectionAttemptError):
        append_collection_attempt(path, invalid)
    assert path.read_bytes() == before
    assert b"SHOULD_NOT_BE_WRITTEN" not in before


@pytest.mark.parametrize("bad_content", [b"not json\n", b"\n"])
def test_corrupt_existing_log_blocks_append_and_preserves_bytes(
    tmp_path: Path, bad_content: bytes
) -> None:
    path = tmp_path / "attempts.jsonl"
    path.write_bytes(bad_content)
    before = path.read_bytes()
    with pytest.raises(CollectionAttemptError):
        append_collection_attempt(path, attempt())
    assert path.read_bytes() == before


def test_self_rehashed_semantic_corruption_is_rejected_on_read(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    record = attempt()
    record["target_minutes_to_kickoff"] = 360
    record = rehash(record)
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")
    with pytest.raises(CollectionAttemptError, match="target minutes"):
        read_collection_attempts(path)


def test_duplicate_target_is_deterministic_and_byte_preserving(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    record = attempt()
    append_collection_attempt(path, record)
    before = path.read_bytes()
    with pytest.raises(CollectionAttemptError, match="already attempted"):
        append_collection_attempt(path, record)
    assert path.read_bytes() == before
