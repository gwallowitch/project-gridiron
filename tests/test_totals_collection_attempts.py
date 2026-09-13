from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from gridiron.market.totals_collection_attempts import (
    TotalsAttemptError,
    append_totals_attempt,
    build_totals_attempt,
    read_totals_attempts,
)

NOW = datetime(2026, 9, 13, 5, tzinfo=UTC)


def attempt(result="FAILED", reason="PROVIDER_ERROR", observation_id=None):
    return build_totals_attempt(game_id="2026_01_ATL_PIT", target_label="T12H", kickoff_at="2026-09-13T17:00:00Z", attempted_at=NOW, result=result, reason_code=reason, observation_id=observation_id)


def test_attempt_roundtrip_and_duplicate_rejected(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    row = attempt()
    append_totals_attempt(path, row)
    assert read_totals_attempts(path) == (row,)
    with pytest.raises(TotalsAttemptError):
        append_totals_attempt(path, row)


@pytest.mark.parametrize("result,reason,linked", [("SUCCESS", "SUCCESS", None), ("FAILED", "PROVIDER_ERROR", "x"), ("FAILED", "SUCCESS", None), ("MISSED_WINDOW", "PROVIDER_ERROR", None), ("POST_KICKOFF", "PROVIDER_ERROR", None)])
def test_attempt_semantics_fail_closed(result, reason, linked) -> None:
    with pytest.raises(TotalsAttemptError):
        attempt(result, reason, linked)


def test_corrupt_attempt_log_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    with pytest.raises(TotalsAttemptError):
        read_totals_attempts(path)
