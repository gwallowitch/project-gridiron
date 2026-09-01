"""Adversarial tests for the synthetic-only operational integration contract."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from test_core_three_provider import authoritative, response
from test_synthetic_contracts import fixture

from gridiron.market.core_three_provider import normalize_event_response
from gridiron.market.synthetic_contracts import (
    ContractError,
    DataPath,
    FailureClass,
    HistoricalRecord,
    PreviewRecord,
    ScheduleState,
)
from gridiron.market.synthetic_integration import (
    AttemptHistory,
    AttemptKind,
    AttemptRecord,
    AttemptState,
    AuthorityKind,
    DecisionState,
    DefEpaInput,
    DefEpaState,
    FrozenCandidateContract,
    IntegrationError,
    SyntheticOperationalTransaction,
    build_synthetic_decision_record,
    canonical_digest,
    classify_edge,
    run_synthetic_pipeline,
    synthetic_authority_dependencies,
    transaction_authority_context_binding,
)


def transaction() -> SyntheticOperationalTransaction:
    payload = response()
    truth = authoritative()
    truth["game_id"] = "fixture:game"
    truth["provider_event_id"] = "fixture:provider-event"
    payload["id"] = "fixture:provider-event"
    observation = normalize_event_response(
        payload,
        truth,
        receipt_at="2026-09-09T23:20:00Z",
        timestamp_semantics_approved=True,
        response_id="fixture:response",
    )
    data = fixture()
    prices = (-190, 155)
    acquisition = replace(
        data["record"].acquisition,
        provenance_fingerprint=observation.response_digest,
        draftkings_prices=prices,
    )
    data["record"] = replace(data["record"], acquisition=acquisition)
    data["execution"] = replace(data["execution"], prices=prices)
    activation = __import__(
        "gridiron.market.synthetic_contracts", fromlist=["ActivationContext"]
    ).ActivationContext(
        **data,
        validation_id="fixture:activation-validation",
        finalization_id="fixture:finalization:integration",
    )
    attempts = AttemptHistory(
        (
            AttemptRecord(
                acquisition.attempt_id,
                acquisition.request_id,
                acquisition.response_id,
                activation.schedule.version,
                AttemptKind.INITIAL,
                AttemptState.PENDING,
                schedule_artifact_binding=canonical_digest(activation.schedule),
            ),
        )
    )
    provisional = SyntheticOperationalTransaction(
        activation,
        observation,
        FrozenCandidateContract(),
        DefEpaInput(0.01, "fixture:def-epa", "fixture:vintage", DefEpaState.OBSERVED),
        2026,
        "REG",
        1,
        (),
        attempts,
    )
    authorities = synthetic_authority_dependencies(
        canonical_digest(activation.expected),
        transaction_authority_context_binding(provisional),
        activation.approval.approval_id,
        activation.validation_id,
    )
    return replace(provisional, authorities=authorities)


def reauthorize(tx: SyntheticOperationalTransaction) -> SyntheticOperationalTransaction:
    without_authorities = replace(tx, authorities=())
    authorities = synthetic_authority_dependencies(
        canonical_digest(tx.activation.expected),
        transaction_authority_context_binding(without_authorities),
        tx.activation.approval.approval_id,
        tx.activation.validation_id,
    )
    return replace(without_authorities, authorities=authorities)


def revised_transaction(depth: int = 2) -> SyntheticOperationalTransaction:
    tx = transaction()
    schedules = [tx.activation.schedule]
    kickoff_texts = ("2026-09-10T00:22:00+00:00", "2026-09-10T00:24:00+00:00")
    for number in range(2, depth + 1):
        prior = schedules[-1]
        schedules.append(
            replace(
                prior,
                version=f"fixture:v{number}",
                predecessor=prior.version,
                predecessor_artifact=prior,
                kickoff=type(prior.kickoff)(kickoff_texts[number - 2]),
                state=ScheduleState.REVISED,
            )
        )
    current = schedules[-1]
    acquisition = tx.activation.record.acquisition
    acquisition = replace(
        acquisition,
        timestamps=replace(acquisition.timestamps, kickoff=current.kickoff),
    )
    activation = replace(
        tx.activation,
        record=replace(tx.activation.record, acquisition=acquisition),
        schedule=current,
        schedule_predecessor=schedules[-2],
    )
    observation = replace(tx.observation, kickoff_at=current.kickoff.utc())
    attempts = [
        AttemptRecord(
            "fixture:revision-a1",
            "fixture:revision-r1",
            "fixture:revision-response-1",
            schedules[0].version,
            AttemptKind.INITIAL,
            AttemptState.PENDING,
            schedule_artifact_binding=canonical_digest(schedules[0]),
        )
    ]
    for index, schedule in enumerate(schedules[1:], start=2):
        prior_attempt = attempts[-1]
        attempts.append(
            AttemptRecord(
                f"fixture:supersede-a{index}",
                f"fixture:supersede-r{index}",
                None,
                schedule.version,
                AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
                AttemptState.SUPERSEDED,
                prior_attempt.attempt_id,
                FailureClass.SCHEDULE_CONFLICT,
                schedule_artifact_binding=canonical_digest(schedule),
            )
        )
        supersession = attempts[-1]
        final = index == len(schedules)
        attempts.append(
            AttemptRecord(
                acquisition.attempt_id if final else f"fixture:restart-a{index}",
                acquisition.request_id if final else f"fixture:restart-r{index}",
                acquisition.response_id if final else f"fixture:revision-response-{index}",
                schedule.version,
                AttemptKind.RESTART_AFTER_SCHEDULE_REVISION,
                AttemptState.PENDING,
                supersession.attempt_id,
                schedule_artifact_binding=canonical_digest(schedule),
            )
        )
    return reauthorize(
        replace(
            tx,
            activation=activation,
            observation=observation,
            attempts=AttemptHistory(tuple(attempts)),
        )
    )


def test_full_pipeline_is_deterministic_but_never_operational() -> None:
    first = run_synthetic_pipeline(transaction())
    second = run_synthetic_pipeline(transaction())
    assert first.state in (DecisionState.NO_BET, DecisionState.POSITIVE_EDGE_CANDIDATE)
    assert first.decision_record == second.decision_record
    assert first.decision_record.record_digest == second.decision_record.record_digest
    assert not first.real_evidence_write_allowed
    assert not first.external_claims_authenticated
    assert not first.activation_allowed
    assert not first.prospective_evidence


def test_week_one_neutral_missingness_is_explicit() -> None:
    tx = reauthorize(replace(
        transaction(),
        def_epa=DefEpaInput(
            None, "fixture:def-epa", "fixture:vintage", DefEpaState.WEEK_ONE_NEUTRAL
        ),
    ))
    assert build_synthetic_decision_record(tx).def_epa_value == 0.0


@pytest.mark.parametrize(
    "edge,expected",
    [
        (0.01, DecisionState.POSITIVE_EDGE_CANDIDATE),
        (0.0, DecisionState.NO_BET),
        (-0.01, DecisionState.NO_BET),
    ],
)
def test_strict_positive_edge_semantics(edge, expected) -> None:
    assert classify_edge(edge) is expected


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("season", 2025, "WRONG_POPULATION"),
        ("season_type", "POST", "WRONG_POPULATION"),
        ("week", 17, "WRONG_POPULATION_WEEK"),
    ],
)
def test_population_is_fail_closed(field, value, reason) -> None:
    result = run_synthetic_pipeline(replace(transaction(), **{field: value}))
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == (reason,)


def test_missing_schedule_is_rejected_without_fallthrough() -> None:
    tx = transaction()
    with pytest.raises(ContractError, match="FIELD_TYPE_MISMATCH"):
        replace(tx.activation, schedule=None)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("candidate_id", "other", "CANDIDATE_IDENTITY_CHANGED"),
        ("market_coefficient", 4.9, "MARKET_COEFFICIENT_CHANGED"),
        ("def_epa_coefficient", 1.0, "DEF_EPA_COEFFICIENT_CHANGED"),
        ("intercept", -2.5, "INTERCEPT_CHANGED"),
        ("residual_cap", 0.05, "RESIDUAL_CAP_CHANGED"),
        ("eligibility", "nonnegative", "ELIGIBILITY_CHANGED"),
    ],
)
def test_frozen_candidate_cannot_drift(field, value, reason) -> None:
    tx = transaction()
    tx = replace(tx, candidate=replace(tx.candidate, **{field: value}))
    assert run_synthetic_pipeline(tx).validation_failures == (reason,)


@pytest.mark.parametrize(
    "target,reason",
    [
        ("game_id", "GAME_IDENTITY_MISMATCH"),
        ("provider_event_id", "PROVIDER_EVENT_IDENTITY_MISMATCH"),
        ("response_id", "RESPONSE_IDENTITY_MISMATCH"),
        ("provenance_fingerprint", "RESPONSE_FINGERPRINT_MISMATCH"),
    ],
)
def test_acquisition_observation_binding_rejects_mismatch(target, reason) -> None:
    tx = transaction()
    acquisition = replace(tx.activation.record.acquisition, **{target: "fixture:wrong"})
    activation = replace(
        tx.activation, record=replace(tx.activation.record, acquisition=acquisition)
    )
    result = run_synthetic_pipeline(replace(tx, activation=activation))
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == (reason,)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("kind", AuthorityKind.PROVIDER_AUTHENTICATION, "DUPLICATE_OR_WRONG_AUTHORITY"),
        ("subject_binding", "0" * 64, "AUTHORITY_SUBJECT_MISMATCH"),
        ("context_binding", "0" * 64, "AUTHORITY_CONTEXT_MISMATCH"),
        ("approval_id", "fixture:wrong", "AUTHORITY_APPROVAL_MISMATCH"),
        ("validation_id", "fixture:wrong", "AUTHORITY_VALIDATION_MISMATCH"),
        ("artifact_id", "fixture:wrong", "AUTHORITY_ARTIFACT_MISMATCH"),
    ],
)
def test_authority_dependencies_are_identity_bound(field, value, reason) -> None:
    tx = transaction()
    changed = list(tx.authorities)
    index = 1 if field == "kind" else 0
    changed[index] = replace(changed[index], **{field: value})
    assert run_synthetic_pipeline(replace(tx, authorities=tuple(changed))).validation_failures == (
        reason,
    )


def test_wrong_data_path_cannot_cross_into_pipeline() -> None:
    tx = transaction()
    boundary = replace(tx.activation.record.boundary, path=DataPath.HISTORICAL)
    activation = replace(
        tx.activation, record=replace(tx.activation.record, boundary=boundary)
    )
    assert run_synthetic_pipeline(replace(tx, activation=activation)).validation_failures == (
        "WRONG_PATH",
    )


@pytest.mark.parametrize(
    "foreign",
    [HistoricalRecord("fixture:historical"), PreviewRecord("fixture:preview"), None],
)
def test_foreign_record_types_reject_without_exception(foreign) -> None:
    result = run_synthetic_pipeline(foreign)
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == ("WRONG_TRANSACTION_TYPE",)


@pytest.mark.parametrize(
    "attempt,reason",
    [
        (
            AttemptRecord(
                "fixture:other", "fixture:request", "fixture:response", "fixture:v1",
                AttemptKind.INITIAL, AttemptState.PENDING,
                schedule_artifact_binding=canonical_digest(fixture()["schedule"]),
            ),
            "ATTEMPT_IDENTITY_MISMATCH",
        ),
        (
            AttemptRecord(
                "fixture:attempt", "fixture:request", None, "fixture:v1",
                AttemptKind.INITIAL, AttemptState.TIMED_OUT, failure=FailureClass.TIMEOUT,
                schedule_artifact_binding=canonical_digest(fixture()["schedule"]),
            ),
            "CURRENT_ATTEMPT_NOT_PENDING",
        ),
    ],
)
def test_attempt_identity_and_terminal_state_are_enforced(attempt, reason) -> None:
    tx = reauthorize(replace(transaction(), attempts=AttemptHistory((attempt,))))
    assert run_synthetic_pipeline(tx).validation_failures == (reason,)


def test_retry_requires_unique_request_and_failed_predecessor() -> None:
    first = AttemptRecord(
        "fixture:a1", "fixture:r1", "fixture:response-1", "fixture:v1",
        AttemptKind.INITIAL, AttemptState.REJECTED, failure=FailureClass.PROVIDER_OUTAGE,
    )
    duplicate = AttemptRecord(
        "fixture:a2", "fixture:r1", "fixture:response", "fixture:v1",
        AttemptKind.RETRY_AFTER_REJECTION, AttemptState.PENDING, "fixture:a1",
    )
    with pytest.raises(IntegrationError, match="DUPLICATE_REQUEST"):
        AttemptHistory((first, duplicate)).validate()


def test_valid_timeout_retry_has_no_invented_network_timing() -> None:
    first = AttemptRecord(
        "fixture:a1", "fixture:r1", None, "fixture:v1", AttemptKind.INITIAL,
        AttemptState.TIMED_OUT, failure=FailureClass.TIMEOUT,
    )
    retry = AttemptRecord(
        "fixture:a2", "fixture:r2", "fixture:response", "fixture:v1",
        AttemptKind.RETRY_AFTER_TIMEOUT, AttemptState.PENDING, "fixture:a1",
    )
    history = AttemptHistory((first, retry))
    history.validate()
    assert not history.timeout_policy_externally_established


def test_schedule_change_can_only_void_an_accepted_attempt_explicitly() -> None:
    accepted = AttemptRecord(
        "fixture:a1", "fixture:r1", "fixture:response", "fixture:v1",
        AttemptKind.INITIAL, AttemptState.ACCEPTED,
    )
    void = AttemptRecord(
        "fixture:a2", "fixture:r2", None, "fixture:v2",
        AttemptKind.VOID_AFTER_SCHEDULE_REVISION, AttemptState.VOIDED, "fixture:a1",
        FailureClass.SCHEDULE_CONFLICT,
    )
    AttemptHistory((accepted, void)).validate()
    with pytest.raises(IntegrationError, match="VOID_REQUIRES_NEW_SCHEDULE"):
        AttemptHistory((accepted, replace(void, schedule_version="fixture:v1"))).validate()


def test_decision_record_cannot_be_forged_or_mutated() -> None:
    record = build_synthetic_decision_record(transaction())
    with pytest.raises(IntegrationError, match="DECISION_DERIVATION_MISMATCH"):
        replace(record, edge=record.edge + 0.01)
    with pytest.raises((FrozenInstanceError, TypeError)):
        record.edge = 1.0


def test_response_content_change_changes_structural_identity() -> None:
    payload = deepcopy(response())
    truth = authoritative()
    truth.update(game_id="fixture:game", provider_event_id="fixture:provider-event")
    payload["id"] = "fixture:provider-event"
    payload["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = 160
    changed = normalize_event_response(
        payload, truth, receipt_at="2026-09-09T23:20:00Z",
        timestamp_semantics_approved=True, response_id="fixture:response",
    )
    assert changed.response_digest != transaction().observation.response_digest


def test_market_tampering_with_stale_digest_rejects_on_authority_context() -> None:
    tx = transaction()
    book = tx.observation.books[0]
    market = book.markets[0]
    outcome = market.outcomes[0]
    altered = replace(
        tx.observation,
        books=(
            replace(
                book,
                markets=(
                    replace(
                        market,
                        outcomes=(replace(outcome, price=outcome.price + 25), market.outcomes[1]),
                    ),
                    *book.markets[1:],
                ),
            ),
            *tx.observation.books[1:],
        ),
    )
    assert altered.response_digest == tx.observation.response_digest
    result = run_synthetic_pipeline(replace(tx, observation=altered))
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == ("AUTHORITY_CONTEXT_MISMATCH",)


@pytest.mark.parametrize(
    "market_index,outcome_index,changes,reason",
    [
        (0, 0, {"price": 0}, "MALFORMED_PRICE"),
        (1, 0, {"point": 4.0}, "CONFLICTING_SPREAD"),
        (2, 0, {"name": "Something"}, "TOTAL_OUTCOME_MISMATCH"),
    ],
)
def test_forged_normalized_market_rejects_even_with_regenerated_fixture_authority(
    market_index, outcome_index, changes, reason
) -> None:
    tx = transaction()
    book = tx.observation.books[0]
    market = book.markets[market_index]
    outcomes = list(market.outcomes)
    outcomes[outcome_index] = replace(outcomes[outcome_index], **changes)
    markets = list(book.markets)
    markets[market_index] = replace(market, outcomes=tuple(outcomes))
    observation = replace(
        tx.observation,
        books=(replace(book, markets=tuple(markets)), *tx.observation.books[1:]),
    )
    forged = reauthorize(replace(tx, observation=observation))
    assert run_synthetic_pipeline(forged).validation_failures == (reason,)


def test_independently_valid_foreign_authorities_cannot_be_substituted() -> None:
    tx = transaction()
    foreign_context = replace(tx, def_epa=replace(tx.def_epa, value=0.02), authorities=())
    foreign = synthetic_authority_dependencies(
        canonical_digest(foreign_context.activation.expected),
        transaction_authority_context_binding(foreign_context),
        foreign_context.activation.approval.approval_id,
        foreign_context.activation.validation_id,
    )
    assert run_synthetic_pipeline(replace(tx, authorities=foreign)).validation_failures == (
        "AUTHORITY_CONTEXT_MISMATCH",
    )


def test_numeric_overflow_is_a_rejected_result_not_an_escaped_exception() -> None:
    tx = transaction()
    tx = replace(tx, def_epa=replace(tx.def_epa, value=-1e308))
    result = run_synthetic_pipeline(tx)
    assert result.state is DecisionState.REJECTED
    assert result.decision_record is None


def test_rejected_response_cannot_be_reused_by_retry() -> None:
    rejected = AttemptRecord(
        "fixture:a1",
        "fixture:r1",
        "fixture:response",
        "fixture:v1",
        AttemptKind.INITIAL,
        AttemptState.REJECTED,
        failure=FailureClass.PROVIDER_OUTAGE,
    )
    retry = AttemptRecord(
        "fixture:a2",
        "fixture:r2",
        "fixture:response",
        "fixture:v1",
        AttemptKind.RETRY_AFTER_REJECTION,
        AttemptState.PENDING,
        "fixture:a1",
    )
    with pytest.raises(IntegrationError, match="DUPLICATE_RESPONSE"):
        AttemptHistory((rejected, retry)).validate()


def test_pending_attempt_can_be_superseded_then_restarted_on_revision() -> None:
    pending = AttemptRecord(
        "fixture:a1",
        "fixture:r1",
        "fixture:old-response",
        "fixture:v1",
        AttemptKind.INITIAL,
        AttemptState.PENDING,
    )
    superseded = AttemptRecord(
        "fixture:a2",
        "fixture:r2",
        None,
        "fixture:v2",
        AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
        AttemptState.SUPERSEDED,
        "fixture:a1",
        FailureClass.SCHEDULE_CONFLICT,
    )
    restarted = AttemptRecord(
        "fixture:a3",
        "fixture:r3",
        "fixture:new-response",
        "fixture:v2",
        AttemptKind.RESTART_AFTER_SCHEDULE_REVISION,
        AttemptState.PENDING,
        "fixture:a2",
    )
    AttemptHistory((pending, superseded, restarted)).validate()


def test_attempt_history_rejects_a_fork_to_an_older_predecessor() -> None:
    first = AttemptRecord(
        "fixture:a1", "fixture:r1", "fixture:response-1", "fixture:v1",
        AttemptKind.INITIAL, AttemptState.REJECTED,
        failure=FailureClass.PROVIDER_OUTAGE,
    )
    second = AttemptRecord(
        "fixture:a2", "fixture:r2", "fixture:response-2", "fixture:v1",
        AttemptKind.RETRY_AFTER_REJECTION, AttemptState.REJECTED, "fixture:a1",
        FailureClass.PROVIDER_OUTAGE,
    )
    fork = AttemptRecord(
        "fixture:a3", "fixture:r3", "fixture:response-3", "fixture:v1",
        AttemptKind.RETRY_AFTER_REJECTION, AttemptState.PENDING, "fixture:a1",
    )
    with pytest.raises(IntegrationError, match="NONLINEAR_ATTEMPT_CHAIN"):
        AttemptHistory((first, second, fork)).validate()


def fabricated_revision_history(tx: SyntheticOperationalTransaction) -> AttemptHistory:
    return AttemptHistory(
        (
            AttemptRecord(
                "fixture:prior-attempt",
                "fixture:prior-request",
                "fixture:old-response",
                "fixture:foreign-v0",
                AttemptKind.INITIAL,
                AttemptState.PENDING,
            ),
            AttemptRecord(
                "fixture:supersession",
                "fixture:supersession-event",
                None,
                tx.activation.schedule.version,
                AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
                AttemptState.SUPERSEDED,
                "fixture:prior-attempt",
                FailureClass.SCHEDULE_CONFLICT,
            ),
            AttemptRecord(
                tx.activation.record.acquisition.attempt_id,
                tx.activation.record.acquisition.request_id,
                tx.activation.record.acquisition.response_id,
                tx.activation.schedule.version,
                AttemptKind.RESTART_AFTER_SCHEDULE_REVISION,
                AttemptState.PENDING,
                "fixture:supersession",
            ),
        )
    )


def test_scheduled_context_rejects_fabricated_supersession_and_restart() -> None:
    tx = transaction()
    attack = reauthorize(replace(tx, attempts=fabricated_revision_history(tx)))
    result = run_synthetic_pipeline(attack)
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == (
        "ATTEMPT_REVISION_REQUIRES_REVISED_SCHEDULE",
    )


def test_valid_v1_to_v2_revision_restart_is_accepted() -> None:
    result = run_synthetic_pipeline(revised_transaction())
    assert result.state in (DecisionState.NO_BET, DecisionState.POSITIVE_EDGE_CANDIDATE)
    assert result.decision_record is not None
    assert not result.activation_allowed
    assert not result.real_evidence_write_allowed


def test_valid_v1_to_v2_to_v3_revision_restart_is_accepted() -> None:
    result = run_synthetic_pipeline(revised_transaction(3))
    assert result.state in (DecisionState.NO_BET, DecisionState.POSITIVE_EDGE_CANDIDATE)
    assert result.decision_record is not None


def test_foreign_old_attempt_version_rejects_against_real_predecessor() -> None:
    tx = revised_transaction()
    attempts = list(tx.attempts.attempts)
    attempts[0] = replace(attempts[0], schedule_version="fixture:foreign-v0")
    result = run_synthetic_pipeline(
        reauthorize(replace(tx, attempts=AttemptHistory(tuple(attempts))))
    )
    assert result.validation_failures == ("ATTEMPT_SCHEDULE_VERSION_NOT_IN_CHAIN",)


def test_missing_predecessor_artifact_rejects() -> None:
    tx = revised_transaction()
    schedule = replace(tx.activation.schedule, predecessor_artifact=None)
    activation = replace(
        tx.activation, schedule=schedule, schedule_predecessor=None
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED


def test_correct_version_with_wrong_predecessor_object_rejects() -> None:
    tx = revised_transaction()
    substituted = replace(
        tx.activation.schedule_predecessor, source_fingerprint="c" * 64
    )
    schedule = replace(tx.activation.schedule, predecessor_artifact=substituted)
    activation = replace(
        tx.activation,
        schedule=schedule,
        schedule_predecessor=substituted,
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == (
        "ATTEMPT_SCHEDULE_ARTIFACT_BINDING_MISMATCH",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source_fingerprint": "c" * 64},
        {"kickoff": type(fixture()["schedule"].kickoff)("2026-09-10T00:19:00+00:00")},
        {
            "retrieved_at": type(fixture()["schedule"].retrieved_at)(
                "2026-09-09T21:59:00+00:00"
            )
        },
        {"provider_event_id": "fixture:foreign-event"},
        {"game_id": "fixture:foreign-game"},
        {"state": ScheduleState.REVISED},
        {
            "source": replace(
                fixture()["schedule"].source,
                reference="fixture:foreign-schedule-source",
            )
        },
    ],
)
def test_material_predecessor_substitution_cannot_reuse_original_attempt_binding(
    changes,
) -> None:
    tx = revised_transaction()
    substituted = replace(tx.activation.schedule_predecessor, **changes)
    schedule = replace(tx.activation.schedule, predecessor_artifact=substituted)
    activation = replace(
        tx.activation,
        schedule=schedule,
        schedule_predecessor=substituted,
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED


def test_old_attempt_artifact_binding_cannot_name_a_different_schedule_version() -> None:
    tx = revised_transaction()
    attempts = list(tx.attempts.attempts)
    attempts[-1] = replace(
        attempts[-1],
        schedule_artifact_binding=attempts[0].schedule_artifact_binding,
    )
    result = run_synthetic_pipeline(
        reauthorize(replace(tx, attempts=AttemptHistory(tuple(attempts))))
    )
    assert result.validation_failures == (
        "ATTEMPT_SCHEDULE_ARTIFACT_BINDING_MISMATCH",
    )


def test_matching_version_without_correct_artifact_binding_rejects() -> None:
    tx = revised_transaction()
    attempts = list(tx.attempts.attempts)
    attempts[0] = replace(attempts[0], schedule_artifact_binding="f" * 64)
    result = run_synthetic_pipeline(
        reauthorize(replace(tx, attempts=AttemptHistory(tuple(attempts))))
    )
    assert result.validation_failures == (
        "ATTEMPT_SCHEDULE_ARTIFACT_BINDING_MISMATCH",
    )


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("predecessor", "game_id", "fixture:foreign-game"),
        ("current", "game_id", "fixture:foreign-game"),
        ("predecessor", "provider_event_id", "fixture:foreign-event"),
        ("current", "provider_event_id", "fixture:foreign-event"),
    ],
)
def test_schedule_context_identity_substitution_rejects(target, field, value) -> None:
    tx = revised_transaction()
    current = tx.activation.schedule
    predecessor = tx.activation.schedule_predecessor
    if target == "predecessor":
        predecessor = replace(predecessor, **{field: value})
        current = replace(current, predecessor_artifact=predecessor)
    else:
        current = replace(current, **{field: value})
    activation = replace(
        tx.activation, schedule=current, schedule_predecessor=predecessor
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED


@pytest.mark.parametrize(
    "changes",
    [
        {"state": ScheduleState.CANCELLED},
        {"source_available": False},
        {"source_fingerprint": "malformed"},
    ],
)
def test_invalid_predecessor_artifact_rejects(changes) -> None:
    tx = revised_transaction()
    predecessor = replace(tx.activation.schedule_predecessor, **changes)
    current = replace(tx.activation.schedule, predecessor_artifact=predecessor)
    activation = replace(
        tx.activation, schedule=current, schedule_predecessor=predecessor
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED


def test_broken_predecessor_chain_rejects() -> None:
    tx = revised_transaction(3)
    v2 = tx.activation.schedule_predecessor
    broken_v2 = replace(v2, predecessor="fixture:missing", predecessor_artifact=None)
    current = replace(tx.activation.schedule, predecessor_artifact=broken_v2)
    activation = replace(
        tx.activation, schedule=current, schedule_predecessor=broken_v2
    )
    result = run_synthetic_pipeline(reauthorize(replace(tx, activation=activation)))
    assert result.state is DecisionState.REJECTED


def test_cyclic_predecessor_chain_rejects() -> None:
    tx = revised_transaction()
    predecessor = tx.activation.schedule_predecessor
    current = tx.activation.schedule
    object.__setattr__(predecessor, "state", ScheduleState.REVISED)
    object.__setattr__(predecessor, "predecessor", current.version)
    object.__setattr__(predecessor, "predecessor_artifact", current)
    result = run_synthetic_pipeline(tx)
    assert result.state is DecisionState.REJECTED


def test_missing_intermediate_schedule_revision_rejects() -> None:
    tx = revised_transaction(3)
    first = tx.attempts.attempts[0]
    supersede = replace(
        tx.attempts.attempts[-2], predecessor_attempt_id=first.attempt_id
    )
    restart = replace(
        tx.attempts.attempts[-1], predecessor_attempt_id=supersede.attempt_id
    )
    history = AttemptHistory((first, supersede, restart))
    result = run_synthetic_pipeline(reauthorize(replace(tx, attempts=history)))
    assert result.state is DecisionState.REJECTED
    assert result.validation_failures == ("SUPERSEDED_ATTEMPT_PREDECESSOR_MISMATCH",)


def test_old_response_reuse_after_valid_revision_rejects() -> None:
    tx = revised_transaction()
    attempts = list(tx.attempts.attempts)
    attempts[-1] = replace(attempts[-1], response_id=attempts[0].response_id)
    result = run_synthetic_pipeline(
        reauthorize(replace(tx, attempts=AttemptHistory(tuple(attempts))))
    )
    assert result.validation_failures == ("DUPLICATE_RESPONSE",)


def test_canonical_digest_has_deterministic_and_type_explicit_semantics() -> None:
    assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})
    assert canonical_digest(("a", "b")) != canonical_digest(("b", "a"))
    assert canonical_digest(-0.0) != canonical_digest(0.0)
    assert canonical_digest("Case") != canonical_digest("case")
    assert canonical_digest("é") != canonical_digest("e\u0301")
    instant = datetime(2026, 9, 1, 12, tzinfo=UTC)
    offset = instant.astimezone(timezone(timedelta(hours=-5)))
    assert canonical_digest(instant) == canonical_digest(offset)
    for nonfinite in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(IntegrationError, match="NONFINITE_VALUE_IN_BINDING"):
            canonical_digest(nonfinite)


def test_record_is_hashable_and_reconstructs_exactly() -> None:
    first = build_synthetic_decision_record(transaction())
    second = build_synthetic_decision_record(transaction())
    assert first == second
    assert hash(first) == hash(second)
    assert first.transaction_binding == second.transaction_binding
    assert first.replay_identity == second.replay_identity


def test_each_material_single_field_change_changes_authority_context() -> None:
    tx = transaction()
    original = transaction_authority_context_binding(tx)
    acquisition = tx.activation.record.acquisition
    variants = (
        replace(tx, week=2),
        replace(tx, def_epa=replace(tx.def_epa, value=0.02)),
        replace(
            tx,
            activation=replace(
                tx.activation,
                record=replace(
                    tx.activation.record,
                    acquisition=replace(acquisition, request_id="fixture:request-2"),
                ),
            ),
        ),
        replace(
            tx,
            attempts=AttemptHistory(
                (replace(tx.attempts.current, request_id="fixture:request-2"),)
            ),
        ),
        replace(
            tx,
            activation=replace(
                tx.activation,
                reviews=replace(
                    tx.activation.reviews,
                    synthetic_verification=replace(
                        tx.activation.reviews.synthetic_verification,
                        artifact_id="fixture:review-artifact:changed",
                    ),
                ),
            ),
        ),
    )
    assert all(transaction_authority_context_binding(item) != original for item in variants)
