from __future__ import annotations

from copy import deepcopy

import pytest

from gridiron.market.core_three_lifecycle import append_event, validate_chain
from gridiron.market.core_three_types import CoreThreeError

GAME = "2026_01_NE_SEA"


def scheduled():
    return append_event((), {"event_type": "SCHEDULED", "game_id": GAME})


def test_postponed_rescheduled_and_cancelled_are_append_only() -> None:
    original = scheduled()
    postponed = append_event(
        original,
        {"event_type": "GAME_POSTPONED", "game_id": GAME, "recorded_at": "t1"},
    )
    revised = append_event(
        postponed,
        {
            "event_type": "SCHEDULE_REVISION",
            "game_id": GAME,
            "old_kickoff_at": "2026-09-10T00:20:00Z",
            "new_kickoff_at": "2026-09-11T00:20:00Z",
            "detected_at": "2026-09-09T23:00:00Z",
        },
    )
    cancelled = append_event(
        revised,
        {"event_type": "GAME_CANCELLED", "game_id": GAME, "recorded_at": "t3"},
    )
    assert len(original) == 1
    assert [event["event_type"] for event in cancelled] == [
        "SCHEDULED",
        "GAME_POSTPONED",
        "SCHEDULE_REVISION",
        "GAME_CANCELLED",
    ]
    assert all(event["prospective_evidence"] is False for event in cancelled)
    validate_chain(cancelled)


def test_accepted_schedule_change_requires_void_and_no_reacceptance() -> None:
    events = append_event(
        scheduled(), {"event_type": "CAPTURE_ACCEPTED", "game_id": GAME}
    )
    with pytest.raises(CoreThreeError, match="REQUIRES_VOID"):
        append_event(
            events,
            {
                "event_type": "SCHEDULE_REVISION",
                "game_id": GAME,
                "old_kickoff_at": "a",
                "new_kickoff_at": "b",
                "detected_at": "c",
            },
        )
    voided = append_event(
        events,
        {"event_type": "DECISION_VOID_SCHEDULE_CHANGE", "game_id": GAME},
    )
    assert voided[-1]["event_type"] == "DECISION_VOID_SCHEDULE_CHANGE"
    with pytest.raises(CoreThreeError, match="ACCEPTED_CAPTURE_IMMUTABLE"):
        append_event(voided, {"event_type": "CAPTURE_ACCEPTED", "game_id": GAME})


def test_void_without_acceptance_rejects() -> None:
    with pytest.raises(CoreThreeError, match="VOID_REQUIRES_ACCEPTED_CAPTURE"):
        append_event(
            scheduled(),
            {"event_type": "DECISION_VOID_SCHEDULE_CHANGE", "game_id": GAME},
        )


def test_chain_tampering_is_detected() -> None:
    events = list(scheduled())
    events[0] = deepcopy(events[0])
    events[0]["game_id"] = "tampered"
    with pytest.raises(CoreThreeError, match="HASH_MISMATCH"):
        validate_chain(events)
