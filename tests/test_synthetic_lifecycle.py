"""Pure replay and compare-and-swap tests; no filesystem or concurrency service."""

from dataclasses import replace

import pytest
from test_synthetic_contracts import fixture, ts

from gridiron.market.synthetic_contracts import (
    Action,
    ActivationContext,
    Blocker,
    ContractError,
    FinalizationAuthorization,
    GateResult,
    ScheduleState,
    expected_review_reference,
)
from gridiron.market.synthetic_lifecycle import (
    EventKind,
    LifecycleEvent,
    LifecycleState,
    append_lifecycle,
    validate_lifecycle,
)


def event(state, kind, **changes):
    return LifecycleEvent(
        f"fixture:event-{len(state.events)}",
        "fixture:game",
        kind,
        len(state.events),
        ts(),
        **changes,
    )


def scheduled():
    state = LifecycleState()
    return append_lifecycle(
        state, event(state, EventKind.SCHEDULED, schedule=fixture()["schedule"])
    )


def activation_context(**changes):
    data = fixture()
    values = {
        **data,
        "validation_id": "fixture:activation-validation",
        "finalization_id": "fixture:finalization:accepted-result",
        **changes,
    }
    return ActivationContext(**values)


def pending(
    state=None,
    attempt="fixture:attempt",
    response="fixture:response",
    approval_id="fixture:approval",
    validation_id="fixture:activation-validation",
):
    state = scheduled() if state is None else state
    return append_lifecycle(
        state,
        event(
            state,
            EventKind.PENDING,
            attempt_id=attempt,
            response_id=response,
            approval_id=approval_id,
            validation_id=validation_id,
        ),
    )


def accepted():
    state = pending()
    context = activation_context()
    return append_lifecycle(
        state,
        event(
            state,
            EventKind.ACCEPTED,
            attempt_id="fixture:attempt",
            response_id="fixture:response",
            gate=context.evaluate(),
            gate_context=context,
        ),
    )


def finalization(response_id="fixture:response"):
    data = fixture()
    governance = next(
        item for item in data["approval"].dependencies if item.blocker is Blocker.GOVERNANCE
    )
    approval = replace(
        data["approval"],
        approval_id="fixture:finalization-approval",
        actions=(Action.FINALIZE,),
    )
    return FinalizationAuthorization(
        "fixture:finalization:accepted-result",
        approval,
        data["expected"],
        data["scope"],
        "fixture:game",
        response_id,
        "fixture:finalization-provenance:fixture:finalization:accepted-result",
        governance,
    )


def revised_schedule(**changes):
    prior = fixture()["schedule"]
    return replace(
        prior,
        **{
            "state": ScheduleState.REVISED,
            "version": "fixture:v2",
            "predecessor": "fixture:v1",
            "kickoff": ts("2026-09-11T00:20:00Z"),
            "predecessor_artifact": prior,
            **changes,
        },
    )


def test_valid_reject_retry_accept_void_and_finalize_paths():
    state = pending()
    rejected = append_lifecycle(
        state,
        event(
            state,
            EventKind.REJECTED,
            attempt_id="fixture:attempt",
            response_id="fixture:response",
        ),
    )
    retry = pending(rejected, "fixture:attempt-2", "fixture:response-2")
    context = activation_context()
    context = replace(
        context,
        record=replace(
            context.record,
            acquisition=replace(
                context.record.acquisition,
                attempt_id="fixture:attempt-2",
                response_id="fixture:response-2",
                components=tuple(
                    replace(item, response_id="fixture:response-2")
                    for item in context.record.acquisition.components
                ),
            ),
        ),
        execution=replace(context.execution, response_id="fixture:response-2"),
    )
    approved = append_lifecycle(
        retry,
        event(
            retry,
            EventKind.ACCEPTED,
            attempt_id="fixture:attempt-2",
            response_id="fixture:response-2",
            gate=context.evaluate(),
            gate_context=context,
        ),
    )
    validate_lifecycle(append_lifecycle(approved, event(approved, EventKind.VOID)))
    finalized = replace(
        event(
            approved,
            EventKind.FINALIZED,
            finalization=finalization("fixture:response-2"),
        ),
        at=ts("2026-09-10T04:00:00Z"),
    )
    validate_lifecycle(append_lifecycle(approved, finalized))
    assert len(state.events) == 2


def test_postponed_requires_revision_and_cancellation_terminal():
    state = scheduled()
    state = append_lifecycle(state, event(state, EventKind.POSTPONED))
    with pytest.raises(ContractError):
        pending(state)
    revised = append_lifecycle(
        state, event(state, EventKind.REVISED, schedule=revised_schedule())
    )
    validate_lifecycle(pending(revised))
    cancelled = append_lifecycle(
        revised,
        event(
            revised,
            EventKind.CANCELLED,
            schedule=replace(revised_schedule(), state=ScheduleState.CANCELLED),
        ),
    )
    with pytest.raises(ContractError, match="CANCELLED_TERMINAL"):
        pending(cancelled)


@pytest.mark.parametrize("state", [LifecycleState(), scheduled()])
def test_orphan_acceptance(state):
    with pytest.raises(ContractError, match="ORPHAN"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=GateResult(True, ()),
            ),
        )


def test_rejected_cannot_mutate_to_accepted():
    state = pending()
    state = append_lifecycle(
        state,
        event(
            state,
            EventKind.REJECTED,
            attempt_id="fixture:attempt",
            response_id="fixture:response",
        ),
    )
    with pytest.raises(ContractError, match="TERMINAL_NO_MUTATION"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=GateResult(True, ()),
            ),
        )


def test_concurrent_acceptance_and_compare_and_swap():
    state = pending()
    state = pending(state, "fixture:attempt-2", "fixture:response-2")
    context = activation_context()
    first = event(
        state,
        EventKind.ACCEPTED,
        attempt_id="fixture:attempt",
        response_id="fixture:response",
        gate=context.evaluate(),
        gate_context=context,
    )
    second = replace(
        first,
        event_id="fixture:concurrent",
        attempt_id="fixture:attempt-2",
        response_id="fixture:response-2",
    )
    winner = append_lifecycle(state, first)
    with pytest.raises(ContractError, match="CONCURRENT_REVISION"):
        append_lifecycle(winner, second)
    with pytest.raises(ContractError, match="DUPLICATE_ACCEPTANCE"):
        append_lifecycle(winner, replace(second, expected_revision=len(winner.events)))


def test_void_forbids_recapture_and_illegal_supersession():
    state = accepted()
    with pytest.raises(ContractError, match="ILLEGAL_SUPERSESSION"):
        append_lifecycle(state, event(state, EventKind.SUPERSEDED))
    with pytest.raises(ContractError, match="REQUIRES_VOID"):
        append_lifecycle(
            state, event(state, EventKind.REVISED, schedule=revised_schedule())
        )
    voided = append_lifecycle(state, event(state, EventKind.VOID))
    with pytest.raises(ContractError, match="NOT_CAPTURABLE"):
        pending(voided, "fixture:new", "fixture:new")


@pytest.mark.parametrize(
    "change",
    [
        {"predecessor": "foreign"},
        {"version": "fixture:v1"},
        {"game_id": "foreign"},
        {"source_available": False},
        {"provider_event_id": "foreign"},
    ],
)
def test_invalid_schedule_revision(change):
    state = scheduled()
    with pytest.raises(ContractError):
        append_lifecycle(
            state, event(state, EventKind.REVISED, schedule=revised_schedule(**change))
        )


def test_prior_pending_attempt_cannot_use_superseded_schedule():
    state = pending()
    state = append_lifecycle(
        state, event(state, EventKind.REVISED, schedule=revised_schedule())
    )
    with pytest.raises(ContractError, match="SUPERSEDED_SCHEDULE"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=GateResult(True, ()),
            ),
        )


@pytest.mark.parametrize("state", [scheduled(), pending(), accepted()])
def test_invalid_finalization(state):
    with pytest.raises(ContractError):
        append_lifecycle(state, event(state, EventKind.FINALIZED))


def test_replay_detects_tampered_history_and_no_approval_gate():
    state = pending()
    with pytest.raises(ContractError, match="GATE_CONTEXT_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
            ),
        )
    with pytest.raises(ContractError, match="DUPLICATE_EVENT"):
        append_lifecycle(
            state,
            replace(
                event(state, EventKind.REJECTED), event_id=state.events[0].event_id
            ),
        )
    forged = LifecycleState(
        (replace(state.events[0], kind=EventKind.ACCEPTED), *state.events[1:])
    )
    with pytest.raises(ContractError, match="ORPHAN"):
        validate_lifecycle(forged)


def test_contradictory_and_forged_gate_results_cannot_authorize_acceptance():
    state = pending()
    context = activation_context()
    contradictory = replace(context.evaluate(), reasons=("MISSING_AUTHORIZATION",))
    with pytest.raises(ContractError, match="SYNTHETIC_GATE_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=contradictory,
                gate_context=context,
            ),
        )
    forged = GateResult(
        True,
        (),
        "fixture:game",
        "fixture:response",
        "fixture:approval",
        "fixture:activation-validation",
    )
    with pytest.raises(ContractError, match="GATE_CONTEXT_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=forged,
            ),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("game_id", "fixture:other-game"),
        ("response_id", "fixture:other-response"),
        ("approval_id", "fixture:other-approval"),
        ("validation_id", "fixture:other-validation"),
    ],
)
def test_gate_receipt_identity_mismatch_rejected(field, value):
    state = pending()
    context = activation_context()
    forged = replace(context.evaluate(), **{field: value})
    with pytest.raises(ContractError, match="SYNTHETIC_GATE_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=forged,
                gate_context=context,
            ),
        )


@pytest.mark.parametrize("binding", ["approval", "validation"])
def test_revalidated_gate_must_match_pending_identity(binding):
    state = pending()
    context = activation_context()
    if binding == "approval":
        context = replace(
            context,
            approval=replace(context.approval, approval_id="fixture:other-approval"),
        )
    else:
        context = replace(context, validation_id="fixture:other-validation")
    with pytest.raises(ContractError, match="SYNTHETIC_GATE_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=context.evaluate(),
                gate_context=context,
            ),
        )


def test_genuine_revalidated_synthetic_gate_authorizes_only_fixture_acceptance():
    state = pending()
    context = activation_context()
    result = context.evaluate()
    accepted_state = append_lifecycle(
        state,
        event(
            state,
            EventKind.ACCEPTED,
            attempt_id="fixture:attempt",
            response_id="fixture:response",
            gate=result,
            gate_context=context,
        ),
    )
    assert accepted_state.events[-1].kind is EventKind.ACCEPTED
    assert not result.real_evidence_write_allowed
    assert not result.external_claims_authenticated


def test_finalize_requires_action_subject_and_provenance_binding():
    state = accepted()
    at = ts("2026-09-10T04:00:00Z")

    with pytest.raises(ContractError, match="AUTHORITY_UNRESOLVED"):
        append_lifecycle(state, replace(event(state, EventKind.FINALIZED), at=at))

    wrong_action = finalization()
    wrong_action = replace(
        wrong_action,
        approval=replace(wrong_action.approval, actions=(Action.EVIDENCE,)),
    )
    with pytest.raises(ContractError, match="ACTION_NOT_PERMITTED"):
        append_lifecycle(
            state,
            replace(
                event(state, EventKind.FINALIZED, finalization=wrong_action), at=at
            ),
        )

    wrong_subject = finalization()
    wrong_subject = replace(
        wrong_subject,
        subject=replace(wrong_subject.subject, implementation_id="fixture:other"),
    )
    with pytest.raises(ContractError, match="FINALIZATION_SUBJECT_MISMATCH"):
        append_lifecycle(
            state,
            replace(
                event(state, EventKind.FINALIZED, finalization=wrong_subject), at=at
            ),
        )

    arbitrary = replace(finalization(), provenance_reference="fixture:arbitrary")
    with pytest.raises(ContractError, match="FINALIZATION_PROVENANCE_REQUIRED"):
        append_lifecycle(
            state,
            replace(event(state, EventKind.FINALIZED, finalization=arbitrary), at=at),
        )

    finalized = append_lifecycle(
        state,
        replace(
            event(state, EventKind.FINALIZED, finalization=finalization()), at=at
        ),
    )
    assert finalized.events[-1].kind is EventKind.FINALIZED


def test_schedule_revision_replay_rejects_self_reference_like_standalone_gate():
    state = scheduled()
    self_reference = revised_schedule(predecessor="fixture:v2")
    with pytest.raises(ContractError, match="SELF_REFERENCING_REVISION"):
        append_lifecycle(
            state,
            event(state, EventKind.REVISED, schedule=self_reference),
        )
    valid = append_lifecycle(
        state,
        event(state, EventKind.REVISED, schedule=revised_schedule()),
    )
    assert valid.events[-1].kind is EventKind.REVISED


def context_with_validation(context, validation_id):
    reviews = context.reviews

    def rebound(review):
        return replace(
            review,
            claim=replace(
                review.claim,
                reference=expected_review_reference(
                    review.role,
                    review.subject,
                    context.approval.approval_id,
                    validation_id,
                ),
            ),
        )

    return replace(
        context,
        validation_id=validation_id,
        reviews=replace(
            reviews,
            synthetic_verification=rebound(reviews.synthetic_verification),
            authorized_conformance=rebound(reviews.authorized_conformance),
            independent_review=rebound(reviews.independent_review),
        ),
    )


@pytest.mark.parametrize("change", ["artifact", "claim", "schedule", "approval"])
def test_gate_result_cannot_replay_against_changed_activation_context(change):
    state = pending()
    context = activation_context()
    original = context.evaluate()
    if change == "artifact":
        review = context.reviews.synthetic_verification
        changed = replace(
            context,
            reviews=replace(
                context.reviews,
                synthetic_verification=replace(
                    review, artifact_id="fixture:wrong-artifact"
                ),
            ),
        )
    elif change == "claim":
        review = context.reviews.independent_review
        changed = replace(
            context,
            reviews=replace(
                context.reviews,
                independent_review=replace(
                    review,
                    claim=replace(review.claim, reference="fixture:foreign-claim"),
                ),
            ),
        )
    elif change == "schedule":
        changed = replace(
            context,
            schedule=replace(context.schedule, source_fingerprint="c" * 64),
        )
    else:
        changed = replace(
            context,
            approval=replace(
                context.approval, authority_reference="fixture:other-authority"
            ),
        )
    with pytest.raises(ContractError, match="SYNTHETIC_GATE_REQUIRED"):
        append_lifecycle(
            state,
            event(
                state,
                EventKind.ACCEPTED,
                attempt_id="fixture:attempt",
                response_id="fixture:response",
                gate=original,
                gate_context=changed,
            ),
        )


def test_material_context_changes_produce_distinct_bindings():
    context = activation_context()
    original = context.evaluate()
    changed_schedule = replace(
        context, schedule=replace(context.schedule, source_fingerprint="c" * 64)
    ).evaluate()
    changed_approval = replace(
        context,
        approval=replace(context.approval, authority_reference="fixture:other-authority"),
    ).evaluate()
    changed_validation = context_with_validation(
        context, "fixture:other-validation"
    ).evaluate()
    assert all(
        result.fixture_conditions_satisfied
        for result in (original, changed_schedule, changed_approval, changed_validation)
    )
    assert len(
        {
            original.context_binding,
            changed_schedule.context_binding,
            changed_approval.context_binding,
            changed_validation.context_binding,
        }
    ) == 4


def test_exact_activation_context_result_still_succeeds():
    state = pending()
    context = activation_context()
    result = context.evaluate()
    accepted_state = append_lifecycle(
        state,
        event(
            state,
            EventKind.ACCEPTED,
            attempt_id="fixture:attempt",
            response_id="fixture:response",
            gate=result,
            gate_context=context,
        ),
    )
    assert accepted_state.events[-1].gate.context_binding == result.context_binding


@pytest.mark.parametrize(
    "change",
    ["both", "identity", "provenance", "foreign"],
)
def test_finalization_identity_must_be_established_by_acceptance_context(change):
    state = accepted()
    authorization = finalization()
    if change == "both":
        authorization = replace(
            authorization,
            finalization_id="fixture:finalization:new",
            provenance_reference="fixture:finalization-provenance:fixture:finalization:new",
        )
    elif change == "identity":
        authorization = replace(
            authorization, finalization_id="fixture:finalization:new"
        )
    elif change == "provenance":
        authorization = replace(
            authorization,
            provenance_reference="fixture:finalization-provenance:fixture:finalization:new",
        )
    else:
        authorization = replace(
            authorization,
            finalization_id="fixture:finalization:foreign",
            provenance_reference=(
                "fixture:finalization-provenance:fixture:finalization:foreign"
            ),
        )
    with pytest.raises(ContractError):
        append_lifecycle(
            state,
            replace(
                event(state, EventKind.FINALIZED, finalization=authorization),
                at=ts("2026-09-10T04:00:00Z"),
            ),
        )


def test_established_finalization_identity_succeeds():
    state = accepted()
    finalized = append_lifecycle(
        state,
        replace(
            event(state, EventKind.FINALIZED, finalization=finalization()),
            at=ts("2026-09-10T04:00:00Z"),
        ),
    )
    assert finalized.events[-1].kind is EventKind.FINALIZED


def test_lifecycle_valid_three_version_schedule_chain_succeeds():
    state = scheduled()
    state = append_lifecycle(
        state, event(state, EventKind.REVISED, schedule=revised_schedule())
    )
    v2 = state.events[-1].schedule
    v3 = replace(
        v2,
        version="fixture:v3",
        predecessor=v2.version,
        predecessor_artifact=v2,
        kickoff=ts("2026-09-12T00:20:00Z"),
    )
    state = append_lifecycle(
        state,
        replace(
            event(state, EventKind.REVISED, schedule=v3),
            at=ts("2026-09-11T23:20:00Z"),
        ),
    )
    assert state.events[-1].schedule.version == "fixture:v3"
