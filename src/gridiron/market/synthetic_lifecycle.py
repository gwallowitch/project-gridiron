"""Pure synthetic state-machine replay. No ledger, persistence, or real authority."""

from dataclasses import dataclass
from enum import StrEnum

from gridiron.market.synthetic_contracts import (
    ActivationContext,
    Blocker,
    Contract,
    FinalizationAuthorization,
    GateResult,
    ScheduleState,
    ScheduleVersion,
    Timestamp,
    require,
)


class EventKind(StrEnum):
    SCHEDULED = "SCHEDULED"
    POSTPONED = "POSTPONED"
    REVISED = "REVISED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    VOID = "VOID"
    FINALIZED = "FINALIZED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class LifecycleEvent(Contract):
    event_id: str
    game_id: str
    kind: EventKind
    expected_revision: int
    at: Timestamp
    attempt_id: str | None = None
    response_id: str | None = None
    approval_id: str | None = None
    validation_id: str | None = None
    schedule: ScheduleVersion | None = None
    gate: GateResult | None = None
    gate_context: ActivationContext | None = None
    finalization: FinalizationAuthorization | None = None


@dataclass(frozen=True, slots=True)
class LifecycleState(Contract):
    events: tuple[LifecycleEvent, ...] = ()


def validate_lifecycle(state: LifecycleState) -> None:
    """Replay semantic transitions, including compare-and-swap revision checks.

    This is an in-memory concurrency model, not a production atomic store.
    SUPERSEDED is derived for an old schedule by REVISED, never for a decision.
    """
    require(type(state) is LifecycleState, "WRONG_LIFECYCLE_TYPE")
    games = {}
    event_ids = set()
    responses = set()
    attempt_ids = set()
    for index, event in enumerate(state.events):
        require(event.expected_revision == index, "CONFLICTING_CONCURRENT_REVISION")
        require(event.event_id not in event_ids, "DUPLICATE_EVENT")
        event_ids.add(event.event_id)
        if index:
            require(
                event.at.utc() >= state.events[index - 1].at.utc(),
                "EVENT_TIME_REGRESSION",
            )
        kind = event.kind
        require(kind is not EventKind.SUPERSEDED, "ILLEGAL_SUPERSESSION")
        if kind is EventKind.SCHEDULED:
            require(event.game_id not in games, "DUPLICATE_SCHEDULE")
            schedule = _schedule(event, ScheduleState.SCHEDULED)
            require(
                schedule.predecessor is None and schedule.predecessor_artifact is None,
                "INITIAL_SCHEDULE_HAS_PREDECESSOR",
            )
            games[event.game_id] = {
                "schedule": schedule,
                "postponed": False,
                "cancelled": False,
                "decision": None,
                "attempts": {},
                "versions": {schedule.version},
                "acceptance_context": None,
            }
            continue
        require(event.game_id in games, "ORPHAN_EVENT")
        game = games[event.game_id]
        require(not game["cancelled"], "CANCELLED_TERMINAL")
        require(game["decision"] is not EventKind.FINALIZED, "FINALIZED_TERMINAL")
        if kind is EventKind.POSTPONED:
            require(
                game["decision"] is None and not game["postponed"],
                "INVALID_POSTPONEMENT",
            )
            game["postponed"] = True
        elif kind is EventKind.REVISED:
            require(game["decision"] is None, "ACCEPTED_REQUIRES_VOID_NO_REVISION")
            revised = _schedule(event, ScheduleState.REVISED)
            prior = game["schedule"]
            require(revised.predecessor != revised.version, "SELF_REFERENCING_REVISION")
            require(
                revised.predecessor_artifact == prior,
                "PREDECESSOR_ARTIFACT_BINDING_MISMATCH",
            )
            require(
                revised.predecessor == prior.version
                and revised.version not in game["versions"],
                "CONFLICTING_SCHEDULE_VERSION",
            )
            require(
                revised.provider_event_id == prior.provider_event_id,
                "REVISION_GAME_MAPPING_CONFLICT",
            )
            require(revised.source == prior.source, "PREDECESSOR_SOURCE_MISMATCH")
            require(
                revised.kickoff.utc() != prior.kickoff.utc(),
                "REVISION_REQUIRES_NEW_KICKOFF",
            )
            game["schedule"] = revised
            game["versions"].add(revised.version)
            game["postponed"] = False
        elif kind is EventKind.CANCELLED:
            require(
                game["decision"] is not EventKind.ACCEPTED, "ACCEPTED_REQUIRES_VOID"
            )
            _schedule(event, ScheduleState.CANCELLED)
            game["cancelled"] = True
        elif kind is EventKind.PENDING:
            require(
                game["decision"] is None and not game["postponed"],
                "GAME_NOT_CAPTURABLE",
            )
            require(
                event.at.utc() < game["schedule"].kickoff.utc(), "CAPTURE_AFTER_KICKOFF"
            )
            require(
                event.attempt_id is not None
                and event.response_id is not None
                and event.approval_id is not None
                and event.validation_id is not None,
                "ATTEMPT_IDENTITY_REQUIRED",
            )
            require(event.attempt_id not in attempt_ids, "DUPLICATE_ATTEMPT")
            attempt_ids.add(event.attempt_id)
            game["attempts"][event.attempt_id] = (
                EventKind.PENDING,
                event.response_id,
                game["schedule"].version,
                event.approval_id,
                event.validation_id,
            )
        elif kind in (EventKind.REJECTED, EventKind.ACCEPTED):
            attempt = game["attempts"].get(event.attempt_id)
            require(attempt is not None, "ORPHAN_ACCEPTANCE_OR_REJECTION")
            require(attempt[0] is EventKind.PENDING, "ATTEMPT_TERMINAL_NO_MUTATION")
            require(event.response_id == attempt[1], "CONFLICTING_RESPONSE_ID")
            if kind is EventKind.ACCEPTED:
                require(game["decision"] is None, "DUPLICATE_ACCEPTANCE_OR_RECAPTURE")
                require(
                    not game["postponed"] and attempt[2] == game["schedule"].version,
                    "POSTPONED_OR_SUPERSEDED_SCHEDULE",
                )
                require(
                    event.at.utc() < game["schedule"].kickoff.utc(),
                    "CAPTURE_AFTER_KICKOFF",
                )
                require(event.response_id not in responses, "REPLAYED_ACCEPTANCE")
                require(
                    type(event.gate_context) is ActivationContext,
                    "SYNTHETIC_GATE_CONTEXT_REQUIRED",
                )
                evaluated = event.gate_context.evaluate()
                require(
                    event.gate is not None
                    and event.gate == evaluated
                    and evaluated.fixture_conditions_satisfied
                    and not evaluated.reasons,
                    "SYNTHETIC_GATE_REQUIRED",
                )
                require(
                    evaluated.game_id == event.game_id
                    and evaluated.response_id == event.response_id
                    and evaluated.approval_id == attempt[3]
                    and evaluated.validation_id == attempt[4],
                    "GATE_CAPTURE_IDENTITY_MISMATCH",
                )
                responses.add(event.response_id)
                game["decision"] = EventKind.ACCEPTED
                game["acceptance_context"] = event.gate_context
            game["attempts"][event.attempt_id] = (kind, event.response_id, attempt[2])
        elif kind is EventKind.VOID:
            require(game["decision"] is EventKind.ACCEPTED, "VOID_REQUIRES_ACCEPTED")
            require(
                event.at.utc() < game["schedule"].kickoff.utc(),
                "VOID_AFTER_KICKOFF_UNSPECIFIED",
            )
            game["decision"] = EventKind.VOID
        elif kind is EventKind.FINALIZED:
            require(
                game["decision"] is EventKind.ACCEPTED, "FINALIZATION_REQUIRES_ACCEPTED"
            )
            require(
                event.at.utc() >= game["schedule"].kickoff.utc(),
                "PREMATURE_FINALIZATION",
            )
            require(
                type(event.finalization) is FinalizationAuthorization,
                "FINALIZATION_AUTHORITY_UNRESOLVED",
            )
            context = game["acceptance_context"]
            require(type(context) is ActivationContext, "ACCEPTANCE_CONTEXT_REQUIRED")
            event.finalization.validate(
                context.expected,
                context.scope,
                event.game_id,
                context.record.acquisition.response_id,
                context.finalization_id,
                event.at,
            )
            game["decision"] = EventKind.FINALIZED


def _schedule(event: LifecycleEvent, expected: ScheduleState) -> ScheduleVersion:
    schedule = event.schedule
    require(schedule is not None, "SCHEDULE_REQUIRED")
    require(
        schedule.game_id == event.game_id and schedule.state is expected,
        "SCHEDULE_IDENTITY_CONFLICT",
    )
    require(schedule.source_available is True, "SCHEDULE_SOURCE_OUTAGE")
    require(schedule.source.blocker is Blocker.SCHEDULE, "WRONG_SCHEDULE_CLAIM")
    schedule.source.require_fixture()
    require(
        len(schedule.source_fingerprint) == 64
        and all(char in "0123456789abcdef" for char in schedule.source_fingerprint),
        "INVALID_SCHEDULE_FINGERPRINT",
    )
    require(
        schedule.retrieved_at.utc() <= schedule.revalidated_at.utc() <= event.at.utc(),
        "SCHEDULE_CHRONOLOGY_CONFLICT",
    )
    if expected is not ScheduleState.CANCELLED:
        require(event.at.utc() < schedule.kickoff.utc(), "INVALID_SCHEDULE_KICKOFF")
    return schedule


def append_lifecycle(state: LifecycleState, event: LifecycleEvent) -> LifecycleState:
    validate_lifecycle(state)
    result = LifecycleState((*state.events, event))
    validate_lifecycle(result)
    return result
