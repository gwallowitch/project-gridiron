"""Synthetic contract tests prove software behavior, never external facts."""

from dataclasses import FrozenInstanceError, replace

import pytest

from gridiron.market.core_three_types import (
    BOOK_KEYS,
    CANDIDATE_VARIANT_ID,
    MARKET_KEYS,
    PROTOCOL_ID,
)
from gridiron.market.synthetic_contracts import (
    AcquisitionEnvelope,
    Action,
    ApprovalEnvelope,
    Blocker,
    ClaimState,
    ContractError,
    DataPath,
    ExecutionScopeEvidence,
    ExternalClaim,
    FailureClass,
    HistoricalRecord,
    JurisdictionClass,
    MarketComponent,
    OperationalFailure,
    OperationalPolicy,
    PathBoundary,
    PreviewRecord,
    ProspectiveFixture,
    RetentionContract,
    RetentionMode,
    ReviewClaim,
    ReviewEvidence,
    ReviewRole,
    Revocation,
    ScheduleState,
    ScheduleVersion,
    Subject,
    Timestamp,
    TimestampContract,
    TimestampMeaning,
    expected_review_artifact,
    expected_review_reference,
    simulate_activation_gate,
    validate_transfer,
)


def ts(text="2026-09-09T23:20:00Z"):
    return Timestamp(text)


def claim(blocker):
    return ExternalClaim(
        blocker, f"fixture:{blocker.value}", ClaimState.SYNTHETIC_VALID
    )


def boundary(path=DataPath.PROSPECTIVE):
    return PathBoundary(
        path, f"synthetic-contract/{path.value}/v1", f"synthetic://{path.value}"
    )


def fixture():
    now = ts()
    effective = ts("2026-09-09T22:00:00Z")
    expiry = ts("2026-09-11T00:00:00Z")
    kickoff = ts("2026-09-10T00:20:00Z")
    subject = Subject(
        PROTOCOL_ID,
        "1",
        CANDIDATE_VARIANT_ID,
        "fixture:spec",
        "fixture:build",
        "fixture:config",
    )
    dependencies = tuple(claim(b) for b in Blocker)
    governance = next(item for item in dependencies if item.blocker is Blocker.GOVERNANCE)
    approval = ApprovalEnvelope(
        "fixture:approval",
        subject,
        "fixture:scope",
        (Action.EVIDENCE,),
        "fixture:governance",
        effective,
        expiry,
        Revocation.NOT_REVOKED_FIXTURE,
        dependencies,
    )
    timing = TimestampContract(
        ts("2026-09-09T23:19:00Z"),
        now,
        now,
        effective,
        kickoff,
        TimestampMeaning.OBSERVATION_FIXTURE,
        claim(Blocker.SEMANTICS),
        "fixture:clock",
    )
    acquisition = AcquisitionEnvelope(
        "fixture:attempt",
        "fixture:request",
        "fixture:game",
        "fixture:provider-event",
        "fixture:response",
        claim(Blocker.PROVIDER),
        ts("2026-09-09T23:19:30Z"),
        timing,
        True,
        "fixture:provenance",
        "a" * 64,
        RetentionMode.QUALIFYING,
        tuple(
            MarketComponent("fixture:response", "fixture:game", book, market, now)
            for book in BOOK_KEYS
            for market in MARKET_KEYS
        ),
        (-150, 130),
    )
    schedule = ScheduleVersion(
        "fixture:game",
        "fixture:provider-event",
        "fixture:v1",
        None,
        claim(Blocker.SCHEDULE),
        "b" * 64,
        effective,
        now,
        kickoff,
        ScheduleState.SCHEDULED,
        True,
    )
    execution = ExecutionScopeEvidence(
        "fixture:feed",
        JurisdictionClass.US_STATE_SPECIFIC,
        "fixture:state",
        "fixture:account",
        "fixture:scope",
        acquisition.response_id,
        (-150, 130),
        True,
        (),
        now,
        expiry,
        claim(Blocker.JURISDICTION),
        claim(Blocker.EXECUTION),
    )
    return {
        "record": ProspectiveFixture(acquisition, boundary()),
        "approval": approval,
        "expected": subject,
        "scope": "fixture:scope",
        "state_reference": "fixture:state",
        "account_reference": "fixture:account",
        "schedule": schedule,
        "execution": execution,
        "retention": RetentionContract(
            RetentionMode.QUALIFYING,
            (RetentionMode.QUALIFYING,),
            claim(Blocker.PERMISSION),
            expiry,
        ),
        "reviews": ReviewEvidence(
            ReviewClaim(
                ReviewRole.SYNTHETIC_VERIFICATION,
                subject,
                expected_review_artifact(ReviewRole.SYNTHETIC_VERIFICATION, subject),
                ExternalClaim(
                    Blocker.GOVERNANCE,
                    expected_review_reference(
                        ReviewRole.SYNTHETIC_VERIFICATION,
                        subject,
                        approval.approval_id,
                        "fixture:activation-validation",
                    ),
                    ClaimState.SYNTHETIC_VALID,
                ),
                governance,
            ),
            ReviewClaim(
                ReviewRole.AUTHORIZED_CONFORMANCE,
                subject,
                expected_review_artifact(ReviewRole.AUTHORIZED_CONFORMANCE, subject),
                ExternalClaim(
                    Blocker.GOVERNANCE,
                    expected_review_reference(
                        ReviewRole.AUTHORIZED_CONFORMANCE,
                        subject,
                        approval.approval_id,
                        "fixture:activation-validation",
                    ),
                    ClaimState.SYNTHETIC_VALID,
                ),
                governance,
            ),
            ReviewClaim(
                ReviewRole.INDEPENDENT_REVIEW,
                subject,
                expected_review_artifact(ReviewRole.INDEPENDENT_REVIEW, subject),
                ExternalClaim(
                    Blocker.GOVERNANCE,
                    expected_review_reference(
                        ReviewRole.INDEPENDENT_REVIEW,
                        subject,
                        approval.approval_id,
                        "fixture:activation-validation",
                    ),
                    ClaimState.SYNTHETIC_VALID,
                ),
                governance,
            ),
        ),
        "now": now,
    }


def mutate_acquisition(data, **changes):
    data["record"] = replace(
        data["record"], acquisition=replace(data["record"].acquisition, **changes)
    )


def mutate_timing(data, **changes):
    mutate_acquisition(
        data, timestamps=replace(data["record"].acquisition.timestamps, **changes)
    )


def test_success_is_only_synthetic_and_immutable():
    result = simulate_activation_gate(**fixture())
    assert result.fixture_conditions_satisfied
    assert not result.real_evidence_write_allowed
    assert not result.external_claims_authenticated
    with pytest.raises((FrozenInstanceError, TypeError)):
        result.real_evidence_write_allowed = True
    with pytest.raises(TypeError):
        simulate_activation_gate(**fixture(), approved=True, activate=True)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("approval", None, "MISSING_AUTHORIZATION"),
        ("scope", "other", "WRONG_SCOPE"),
        ("now", ts("2026-09-11T00:00:00Z"), "EXPIRED"),
        ("now", ts("2026-09-09T21:00:00Z"), "NOT_EFFECTIVE"),
        ("accepted_game_ids", ("fixture:game",), "LATER_PRICE_REPLACEMENT"),
        ("accepted_response_ids", ("fixture:response",), "REPLAYED_ACCEPTANCE"),
    ],
)
def test_gate_denials(field, value, reason):
    data = fixture()
    data[field] = value
    result = simulate_activation_gate(**data)
    assert not result.fixture_conditions_satisfied
    assert reason in result.reasons[0]
    assert not result.real_evidence_write_allowed


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol_id", "foreign"),
        ("version", "2"),
        ("candidate_variant", "seven-book"),
        ("specification_id", "other"),
        ("implementation_id", "other"),
        ("configuration_id", "other"),
    ],
)
def test_subject_binding(field, value):
    data = fixture()
    data["approval"] = replace(
        data["approval"], subject=replace(data["approval"].subject, **{field: value})
    )
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority_reference", "untrusted"),
        ("actions", (Action.BUILD,)),
        ("revocation", Revocation.REVOKED),
        ("revocation", Revocation.UNKNOWN),
        ("effective_at", ts("2026-09-09T22:01:00Z")),
        ("dependencies", ()),
    ],
)
def test_approval_authority_fields(field, value):
    data = fixture()
    data["approval"] = replace(data["approval"], **{field: value})
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize("blocker", list(Blocker))
@pytest.mark.parametrize("state", [ClaimState.UNKNOWN, ClaimState.UNVERIFIED])
def test_every_unresolved_external_claim_blocks(blocker, state):
    data = fixture()
    deps = tuple(
        replace(c, state=state) if c.blocker is blocker else c
        for c in data["approval"].dependencies
    )
    data["approval"] = replace(data["approval"], dependencies=deps)
    assert simulate_activation_gate(**data).reasons == (
        "UNRESOLVED_EXTERNAL_PREREQUISITE",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("complete_response", False),
        ("provenance_fingerprint", "bad"),
        ("draftkings_prices", ()),
        ("draftkings_prices", (-150, 99)),
        ("components", ()),
        ("request_started_at", ts("2026-09-09T23:21:00Z")),
        ("request_started_at", ts("2026-09-09T21:00:00Z")),
    ],
)
def test_acquisition_rejects_partial_and_invalid(field, value):
    data = fixture()
    mutate_acquisition(data, **{field: value})
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "field,value",
    [
        ("response_id", "other"),
        ("game_id", "other"),
        ("receipt", ts("2026-09-09T23:19:00Z")),
    ],
)
def test_mixed_components(field, value):
    data = fixture()
    components = data["record"].acquisition.components
    mutate_acquisition(
        data, components=(replace(components[0], **{field: value}), *components[1:])
    )
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


def test_duplicate_component_and_dependency_binding():
    data = fixture()
    components = data["record"].acquisition.components
    mutate_acquisition(data, components=(components[1], *components[1:]))
    assert simulate_activation_gate(**data).reasons == ("DUPLICATE_OR_WRONG_COMPONENT",)
    data = fixture()
    mutate_acquisition(
        data,
        provider_claim=replace(
            claim(Blocker.PROVIDER), reference="fixture:unapproved-provider"
        ),
    )
    assert simulate_activation_gate(**data).reasons == ("DEPENDENCY_BINDING_MISMATCH",)


@pytest.mark.parametrize("bad", ["invalid", "2026-09-09T23:20:00", "", None])
def test_malformed_timestamp(bad):
    with pytest.raises(ContractError):
        Timestamp(bad)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("provider_timestamp", ts("2026-09-09T23:20:01Z"), "FUTURE_QUOTE"),
        ("provider_timestamp", ts("2026-09-09T23:09:59Z"), "STALE_QUOTE"),
        ("local_clock", ts("2026-09-09T23:20:01Z"), "CLOCK_DISAGREEMENT"),
        ("meaning", TimestampMeaning.UNRESOLVED, "SEMANTIC_AMBIGUITY"),
        ("meaning", TimestampMeaning.PUBLICATION_FIXTURE, "SEMANTIC_AMBIGUITY"),
        ("clock_reference", None, "UNVERIFIED_CLOCK"),
    ],
)
def test_time_contract_rejects(field, value, reason):
    data = fixture()
    mutate_timing(data, **{field: value})
    assert simulate_activation_gate(**data).reasons == (reason,)


def test_timestamp_original_text_and_exact_age_boundary():
    data = fixture()
    stamp = ts("2026-09-09T18:10:00-05:00")
    mutate_timing(data, provider_timestamp=stamp)
    assert stamp.text == "2026-09-09T18:10:00-05:00"
    assert stamp.utc() == ts("2026-09-09T23:10:00Z").utc()
    assert simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "field,value",
    [
        ("game_id", "other"),
        ("provider_event_id", "other"),
        ("kickoff", ts("2026-09-10T00:15:00Z")),
        ("state", ScheduleState.POSTPONED),
        ("state", ScheduleState.CANCELLED),
        ("state", ScheduleState.REVISED),
        ("source_available", False),
        ("revalidated_at", ts("2026-09-09T23:21:00Z")),
    ],
)
def test_schedule_validation(field, value):
    data = fixture()
    data["schedule"] = replace(data["schedule"], **{field: value})
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "field,value",
    [
        ("jurisdiction", JurisdictionClass.UNKNOWN),
        ("jurisdiction", JurisdictionClass.US_AGGREGATE),
        ("state_reference", "fixture:other-state"),
        ("account_reference", "fixture:other-account"),
        ("scope", "other"),
        ("market_available", False),
        ("prices", ()),
        ("prices", (-160, 140)),
        ("restrictions", ("fixture:restricted",)),
        ("expires_at", ts()),
        ("compared_at", ts("2026-09-09T23:19:00Z")),
        ("execution_claim", ExternalClaim(Blocker.EXECUTION, "fixture:execution")),
    ],
)
def test_execution_scope(field, value):
    data = fixture()
    data["execution"] = replace(data["execution"], **{field: value})
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize("mode", list(RetentionMode))
def test_retention_modes_do_not_grant_real_evidence(mode):
    data = fixture()
    data["retention"] = replace(data["retention"], mode=mode, allowed_modes=(mode,))
    mutate_acquisition(data, permission_mode=mode)
    result = simulate_activation_gate(**data)
    assert result.fixture_conditions_satisfied is (mode is RetentionMode.QUALIFYING)
    assert not result.real_evidence_write_allowed


def test_permission_expiry_and_review_requirements():
    data = fixture()
    data["retention"] = replace(data["retention"], expires_at=ts())
    assert simulate_activation_gate(**data).reasons == ("PERMISSION_EXPIRED",)
    for field in (
        "synthetic_verification",
        "authorized_conformance",
        "independent_review",
    ):
        data = fixture()
        attestation = getattr(data["reviews"], field)
        data["reviews"] = replace(
            data["reviews"],
            **{
                field: replace(
                    attestation,
                    claim=ExternalClaim(Blocker.GOVERNANCE, "fixture:review"),
                )
            },
        )
        assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "field,change",
    [
        (
            "synthetic_verification",
            {"role": ReviewRole.INDEPENDENT_REVIEW},
        ),
        (
            "synthetic_verification",
            {"subject": replace(fixture()["expected"], implementation_id="other")},
        ),
        (
            "synthetic_verification",
            {"claim": claim(Blocker.PERMISSION)},
        ),
        (
            "independent_review",
            {"claim": claim(Blocker.PERMISSION)},
        ),
    ],
)
def test_review_role_subject_and_permission_confusion(field, change):
    data = fixture()
    attestation = getattr(data["reviews"], field)
    data["reviews"] = replace(
        data["reviews"], **{field: replace(attestation, **change)}
    )
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize("duplicate", ["artifact_id", "claim"])
def test_duplicate_review_artifacts_and_claims_rejected(duplicate):
    data = fixture()
    verification = data["reviews"].synthetic_verification
    independent = data["reviews"].independent_review
    value = getattr(verification, duplicate)
    data["reviews"] = replace(
        data["reviews"],
        independent_review=replace(independent, **{duplicate: value}),
    )
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


def test_correctly_scoped_distinct_reviews_satisfy_only_synthetic_gate():
    result = simulate_activation_gate(**fixture())
    assert result.fixture_conditions_satisfied
    assert not result.real_evidence_write_allowed
    assert not result.external_claims_authenticated


def test_revised_schedule_requires_valid_non_self_predecessor():
    data = fixture()
    prior = data["schedule"]
    revised_kickoff = ts("2026-09-10T00:25:00Z")
    mutate_timing(data, kickoff=revised_kickoff)
    revised = replace(
        prior,
        version="fixture:v2",
        predecessor=prior.version,
        kickoff=revised_kickoff,
        state=ScheduleState.REVISED,
        predecessor_artifact=prior,
    )
    data["schedule"] = revised
    data["schedule_predecessor"] = prior
    assert simulate_activation_gate(**data).fixture_conditions_satisfied

    data["schedule"] = replace(revised, predecessor=revised.version)
    assert simulate_activation_gate(**data).reasons == ("SELF_REFERENCING_REVISION",)

    data["schedule"] = revised
    data["schedule_predecessor"] = replace(prior, version="fixture:foreign")
    assert simulate_activation_gate(**data).reasons == (
        "PREDECESSOR_ARTIFACT_BINDING_MISMATCH",
    )


def test_revised_schedule_without_history_fails_closed():
    data = fixture()
    revised_kickoff = ts("2026-09-10T00:25:00Z")
    mutate_timing(data, kickoff=revised_kickoff)
    data["schedule"] = replace(
        data["schedule"],
        version="fixture:v2",
        predecessor="fixture:v1",
        kickoff=revised_kickoff,
        state=ScheduleState.REVISED,
    )
    assert simulate_activation_gate(**data).reasons == ("REVISION_HISTORY_REQUIRED",)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_id", "fixture:wrong-artifact"),
        (
            "claim",
            ExternalClaim(
                Blocker.GOVERNANCE,
                "fixture:governance-from-another-context",
                ClaimState.SYNTHETIC_VALID,
            ),
        ),
        ("subject", replace(fixture()["expected"], implementation_id="fixture:other")),
        (
            "governance_dependency",
            replace(
                claim(Blocker.GOVERNANCE), reference="fixture:foreign-governance"
            ),
        ),
    ],
)
def test_review_artifact_and_governance_context_binding(field, value):
    data = fixture()
    review = data["reviews"].synthetic_verification
    data["reviews"] = replace(
        data["reviews"], synthetic_verification=replace(review, **{field: value})
    )
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


def test_review_claim_for_other_validation_context_is_rejected():
    data = fixture()
    review = data["reviews"].independent_review
    foreign = replace(
        review,
        claim=replace(
            review.claim,
            reference=expected_review_reference(
                review.role,
                review.subject,
                data["approval"].approval_id,
                "fixture:other-validation",
            ),
        ),
    )
    data["reviews"] = replace(data["reviews"], independent_review=foreign)
    assert simulate_activation_gate(**data).reasons == ("REVIEW_CONTEXT_MISMATCH",)


@pytest.mark.parametrize(
    "predecessor_change",
    [
        {"state": ScheduleState.CANCELLED},
        {"source_available": False},
        {"predecessor": "fixture:malformed"},
        {"source_fingerprint": "forged"},
    ],
)
def test_invalid_predecessor_artifact_is_rejected(predecessor_change):
    data = fixture()
    prior = data["schedule"]
    invalid = replace(prior, **predecessor_change)
    revised_kickoff = ts("2026-09-10T00:25:00Z")
    mutate_timing(data, kickoff=revised_kickoff)
    data["schedule"] = replace(
        prior,
        version="fixture:v2",
        predecessor=invalid.version,
        predecessor_artifact=invalid,
        kickoff=revised_kickoff,
        state=ScheduleState.REVISED,
    )
    data["schedule_predecessor"] = invalid
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


def test_invalid_schedule_ancestor_is_rejected_and_valid_three_version_chain_passes():
    data = fixture()
    v1 = replace(data["schedule"], kickoff=ts("2026-09-10T00:15:00Z"))
    v2 = replace(
        v1,
        version="fixture:v2",
        predecessor=v1.version,
        predecessor_artifact=v1,
        kickoff=ts("2026-09-10T00:20:00Z"),
        state=ScheduleState.REVISED,
    )
    v3 = replace(
        v2,
        version="fixture:v3",
        predecessor=v2.version,
        predecessor_artifact=v2,
        kickoff=ts("2026-09-10T00:25:00Z"),
    )
    mutate_timing(data, kickoff=v3.kickoff)
    data["schedule"] = v3
    data["schedule_predecessor"] = v2
    assert simulate_activation_gate(**data).fixture_conditions_satisfied

    bad_v1 = replace(v1, source_available=False)
    bad_v2 = replace(v2, predecessor_artifact=bad_v1)
    data["schedule"] = replace(v3, predecessor_artifact=bad_v2)
    data["schedule_predecessor"] = bad_v2
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


@pytest.mark.parametrize(
    "record", [HistoricalRecord("fixture:history"), PreviewRecord("fixture:preview")]
)
@pytest.mark.parametrize("destination", [DataPath.PROSPECTIVE, DataPath.OPERATIONS])
def test_no_historical_preview_promotion(record, destination):
    with pytest.raises(ContractError):
        validate_transfer(record, boundary(destination))
    with pytest.raises(TypeError):
        replace(record, classification="qualifying_evidence")
    data = fixture()
    data["record"] = record
    assert not simulate_activation_gate(**data).fixture_conditions_satisfied


def test_no_backward_flow_or_real_path_and_no_nested_mutability():
    data = fixture()
    for path in (DataPath.HISTORICAL, DataPath.PREVIEW):
        with pytest.raises(ContractError):
            validate_transfer(data["record"], boundary(path))
    with pytest.raises(ContractError):
        replace(boundary(), namespace="data/real-ledger.jsonl").validate()
    with pytest.raises(ContractError):
        replace(
            data["record"].acquisition,
            components=list(data["record"].acquisition.components),
        )
    with pytest.raises(ContractError):
        replace(data["approval"], actions=(True,))


@pytest.mark.parametrize("kind", list(FailureClass))
def test_failure_classification_and_unset_production_policy(kind):
    failure = OperationalFailure(kind, "fixture:attempt")
    assert failure.policy_reference is None
    policy = OperationalPolicy()
    assert (
        policy.timeout_seconds is policy.retry_limit is policy.backoff_seconds is None
    )
    with pytest.raises(ContractError, match="REQUIRED_POLICY_UNSET"):
        policy.require_fixture()


def test_explicit_fixture_policy_only():
    OperationalPolicy(1, 1, (1,), "fixture:policy").require_fixture()
    with pytest.raises(ContractError):
        OperationalPolicy(1, 1, (), "fixture:policy").require_fixture()
