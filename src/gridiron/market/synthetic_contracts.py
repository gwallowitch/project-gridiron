"""PROPOSED interfaces: synthetic simulation only, never real authorization.

External facts are NOT ESTABLISHED BY REPOSITORY EVIDENCE. This module has no
network, credential, filesystem, real evidence writer, or production integration.
SYNTHETIC_VALID is a fixture assertion, not verification of an external claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from gridiron.market.core_three_types import (
    BOOK_KEYS,
    CANDIDATE_VARIANT_ID,
    MARKET_KEYS,
    PROTOCOL_ID,
)


class ContractError(ValueError):
    """Deterministic rejection; messages never echo supplied values."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ContractError(reason)


def structural_digest(value: object) -> str:
    """Bind immutable synthetic contracts without authenticating external facts."""

    def canonical(item: object) -> object:
        if isinstance(item, StrEnum):
            return {"type": type(item).__qualname__, "value": item.value}
        if hasattr(type(item), "__dataclass_fields__"):
            return {
                "type": type(item).__qualname__,
                "fields": [
                    [field.name, canonical(getattr(item, field.name))]
                    for field in fields(item)
                ],
            }
        if isinstance(item, tuple):
            return {"type": "tuple", "items": [canonical(part) for part in item]}
        if item is None or type(item) in (bool, int, str):
            return item
        raise ContractError("UNSUPPORTED_STRUCTURAL_BINDING_TYPE")

    encoded = json.dumps(
        canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matches(value: object, annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin is UnionType:
        return any(_matches(value, member) for member in get_args(annotation))
    if origin is tuple:
        args = get_args(annotation)
        return type(value) is tuple and all(_matches(item, args[0]) for item in value)
    return type(value) is annotation


@dataclass(frozen=True, slots=True)
class Contract:
    """Exact runtime field types; immutable nested contracts/tuples only."""

    def __post_init__(self) -> None:
        hints = get_type_hints(type(self))
        for field in fields(self):
            value = getattr(self, field.name)
            require(_matches(value, hints[field.name]), "FIELD_TYPE_MISMATCH")
            if isinstance(value, str):
                require(bool(value.strip()), "EMPTY_FIELD")


@dataclass(frozen=True, slots=True)
class Timestamp(Contract):
    text: str

    def __post_init__(self) -> None:
        Contract.__post_init__(self)
        self.utc()

    def utc(self) -> datetime:
        try:
            parsed = datetime.fromisoformat(self.text)
        except ValueError:
            raise ContractError("MALFORMED_TIMESTAMP") from None
        require(
            parsed.tzinfo is not None and parsed.utcoffset() is not None,
            "TIMEZONE_REQUIRED",
        )
        return parsed.astimezone(UTC)


class ClaimState(StrEnum):
    UNKNOWN = "UNKNOWN"
    UNVERIFIED = "UNVERIFIED"
    SYNTHETIC_VALID = "SYNTHETIC_VALID"


class Blocker(StrEnum):
    PROVIDER = "provider_origin"
    SEMANTICS = "timestamp_semantics"
    JURISDICTION = "jurisdiction"
    EXECUTION = "account_executability"
    PERMISSION = "retention_permission"
    SCHEDULE = "schedule_authority"
    GOVERNANCE = "governance"
    EFFECTIVE = "effective_time"


@dataclass(frozen=True, slots=True)
class ExternalClaim(Contract):
    blocker: Blocker
    reference: str
    state: ClaimState = ClaimState.UNVERIFIED

    def require_fixture(self) -> None:
        require(
            self.state is ClaimState.SYNTHETIC_VALID, "UNRESOLVED_EXTERNAL_PREREQUISITE"
        )
        require(self.reference.startswith("fixture:"), "SYNTHETIC_REFERENCE_REQUIRED")


class Action(StrEnum):
    BUILD = "build_synthetic"
    CONFORMANCE = "simulate_conformance"
    EVIDENCE = "simulate_evidence_write"
    FINALIZE = "simulate_finalization"


class Revocation(StrEnum):
    UNKNOWN = "UNKNOWN"
    NOT_REVOKED_FIXTURE = "NOT_REVOKED_FIXTURE"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class Subject(Contract):
    protocol_id: str
    version: str
    candidate_variant: str
    specification_id: str
    implementation_id: str
    configuration_id: str

    def validate(self) -> None:
        require(
            self.protocol_id == PROTOCOL_ID and self.version == "1",
            "WRONG_PROTOCOL_VERSION",
        )
        require(
            self.candidate_variant == CANDIDATE_VARIANT_ID, "WRONG_CANDIDATE_VARIANT"
        )


@dataclass(frozen=True, slots=True)
class ApprovalEnvelope(Contract):
    approval_id: str
    subject: Subject
    scope: str
    actions: tuple[Action, ...]
    authority_reference: str
    effective_at: Timestamp
    expires_at: Timestamp
    revocation: Revocation
    dependencies: tuple[ExternalClaim, ...]

    def validate(
        self, expected: Subject, scope: str, action: Action, now: Timestamp
    ) -> None:
        expected.validate()
        self.subject.validate()
        require(self.subject == expected, "APPROVAL_SUBJECT_MISMATCH")
        require(self.scope == scope, "WRONG_SCOPE")
        require(action in self.actions, "ACTION_NOT_PERMITTED")
        require(len(self.actions) == len(set(self.actions)), "DUPLICATE_ACTION")
        require(
            self.authority_reference.startswith("fixture:"),
            "SYNTHETIC_AUTHORITY_REQUIRED",
        )
        require(
            self.revocation is Revocation.NOT_REVOKED_FIXTURE,
            "REVOKED_OR_UNVERIFIED_APPROVAL",
        )
        require(
            self.effective_at.utc() < self.expires_at.utc(), "INVALID_APPROVAL_INTERVAL"
        )
        require(
            self.effective_at.utc() <= now.utc() < self.expires_at.utc(),
            "APPROVAL_NOT_EFFECTIVE_OR_EXPIRED",
        )
        require(len(self.dependencies) == len(Blocker), "MISSING_DEPENDENCIES")
        require(
            {claim.blocker for claim in self.dependencies} == set(Blocker),
            "CONFLICTING_DEPENDENCIES",
        )
        for claim in self.dependencies:
            claim.require_fixture()


class TimestampMeaning(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    OBSERVATION_FIXTURE = "OBSERVATION_FIXTURE"
    PUBLICATION_FIXTURE = "PUBLICATION_FIXTURE"


@dataclass(frozen=True, slots=True)
class TimestampContract(Contract):
    provider_timestamp: Timestamp
    receipt: Timestamp
    local_clock: Timestamp
    effective_authorization: Timestamp
    kickoff: Timestamp
    meaning: TimestampMeaning = TimestampMeaning.UNRESOLVED
    semantics: ExternalClaim | None = None
    clock_reference: str | None = None

    def validate(self) -> None:
        require(
            self.meaning is TimestampMeaning.OBSERVATION_FIXTURE, "SEMANTIC_AMBIGUITY"
        )
        require(
            self.semantics is not None and self.semantics.blocker is Blocker.SEMANTICS,
            "SEMANTIC_AMBIGUITY",
        )
        self.semantics.require_fixture()
        require(
            self.clock_reference is not None
            and self.clock_reference.startswith("fixture:"),
            "UNVERIFIED_CLOCK",
        )
        require(self.local_clock.utc() == self.receipt.utc(), "CLOCK_DISAGREEMENT")
        age = self.receipt.utc() - self.provider_timestamp.utc()
        require(age >= timedelta(0), "FUTURE_QUOTE")
        require(age <= timedelta(minutes=10), "STALE_QUOTE")
        require(
            self.receipt.utc() >= self.effective_authorization.utc(),
            "BEFORE_EFFECTIVE_TIME",
        )
        window = self.kickoff.utc() - self.receipt.utc()
        require(
            timedelta(minutes=55) <= window <= timedelta(minutes=65),
            "OUTSIDE_CAPTURE_WINDOW",
        )


class RetentionMode(StrEnum):
    NONE = "no_retention"
    PERMITTED = "permitted_retention"
    REJECTED = "rejected_sanitized"
    REVIEW = "review_copy"
    QUALIFYING = "qualifying_evidence_simulation"
    MANIFEST = "manifest_simulation"
    LEDGER = "ledger_simulation"


class DataPath(StrEnum):
    HISTORICAL = "historical"
    PREVIEW = "preview"
    PROSPECTIVE = "prospective_simulation"
    OPERATIONS = "operations_simulation"


@dataclass(frozen=True, slots=True)
class PathBoundary(Contract):
    path: DataPath
    schema: str
    namespace: str

    def validate(self) -> None:
        # Logical identifiers only; no filesystem paths or stores are opened.
        require(
            self.schema == f"synthetic-contract/{self.path.value}/v1",
            "WRONG_PATH_SCHEMA",
        )
        require(
            self.namespace == f"synthetic://{self.path.value}", "WRONG_PATH_NAMESPACE"
        )


@dataclass(frozen=True, slots=True)
class RetentionContract(Contract):
    mode: RetentionMode
    allowed_modes: tuple[RetentionMode, ...]
    permission: ExternalClaim
    expires_at: Timestamp

    def validate(self, now: Timestamp) -> None:
        require(self.permission.blocker is Blocker.PERMISSION, "WRONG_PERMISSION_CLAIM")
        self.permission.require_fixture()
        require(now.utc() < self.expires_at.utc(), "PERMISSION_EXPIRED")
        require(self.mode in self.allowed_modes, "RETENTION_MODE_NOT_PERMITTED")
        require(
            len(self.allowed_modes) == len(set(self.allowed_modes)),
            "DUPLICATE_RETENTION_MODE",
        )


@dataclass(frozen=True, slots=True)
class MarketComponent(Contract):
    response_id: str
    game_id: str
    book: str
    market: str
    receipt: Timestamp


@dataclass(frozen=True, slots=True)
class AcquisitionEnvelope(Contract):
    attempt_id: str
    request_id: str
    game_id: str
    provider_event_id: str
    response_id: str
    provider_claim: ExternalClaim
    request_started_at: Timestamp
    timestamps: TimestampContract
    complete_response: bool
    provenance_reference: str
    provenance_fingerprint: str
    permission_mode: RetentionMode
    components: tuple[MarketComponent, ...]
    draftkings_prices: tuple[int, ...]

    def validate(self) -> None:
        require(self.provider_claim.blocker is Blocker.PROVIDER, "WRONG_PROVIDER_CLAIM")
        self.provider_claim.require_fixture()
        require(self.complete_response is True, "INCOMPLETE_RESPONSE")
        require(
            self.provenance_reference.startswith("fixture:"),
            "SYNTHETIC_PROVENANCE_REQUIRED",
        )
        require(
            len(self.provenance_fingerprint) == 64
            and all(c in "0123456789abcdef" for c in self.provenance_fingerprint),
            "MALFORMED_FINGERPRINT",
        )
        self.timestamps.validate()
        require(
            self.timestamps.effective_authorization.utc()
            <= self.request_started_at.utc()
            <= self.timestamps.receipt.utc(),
            "INVALID_REQUEST_CHRONOLOGY",
        )
        require(len(self.components) == 9, "INCOMPLETE_COMPONENTS")
        expected = {(book, market) for book in BOOK_KEYS for market in MARKET_KEYS}
        require(
            {(c.book, c.market) for c in self.components} == expected,
            "DUPLICATE_OR_WRONG_COMPONENT",
        )
        for component in self.components:
            require(
                component.response_id == self.response_id
                and component.game_id == self.game_id,
                "MIXED_RESPONSE_OR_GAME",
            )
            require(
                component.receipt.utc() == self.timestamps.receipt.utc(),
                "CONFLICTING_RECEIPT",
            )
        require(
            len(self.draftkings_prices) == 2
            and all(abs(p) >= 100 for p in self.draftkings_prices),
            "DRAFTKINGS_PRICE_UNAVAILABLE",
        )


class ScheduleState(StrEnum):
    SCHEDULED = "SCHEDULED"
    POSTPONED = "POSTPONED"
    REVISED = "REVISED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ScheduleVersion(Contract):
    game_id: str
    provider_event_id: str
    version: str
    predecessor: str | None
    source: ExternalClaim
    source_fingerprint: str
    retrieved_at: Timestamp
    revalidated_at: Timestamp
    kickoff: Timestamp
    state: ScheduleState
    source_available: bool
    predecessor_artifact: ScheduleVersion | None = None

    def validate(
        self,
        acquisition: AcquisitionEnvelope,
        predecessor: ScheduleVersion | None = None,
    ) -> None:
        require(self.source_available is True, "SCHEDULE_SOURCE_OUTAGE")
        require(self.source.blocker is Blocker.SCHEDULE, "WRONG_SCHEDULE_CLAIM")
        self.source.require_fixture()
        require(
            len(self.source_fingerprint) == 64
            and all(char in "0123456789abcdef" for char in self.source_fingerprint),
            "INVALID_SCHEDULE_FINGERPRINT",
        )
        require(
            self.state in (ScheduleState.SCHEDULED, ScheduleState.REVISED),
            "SCHEDULE_NOT_CAPTURABLE",
        )
        require(
            self.game_id == acquisition.game_id
            and self.provider_event_id == acquisition.provider_event_id,
            "EXACT_GAME_MAPPING_REQUIRED",
        )
        require(
            self.kickoff.utc() == acquisition.timestamps.kickoff.utc(),
            "KICKOFF_MISMATCH",
        )
        require(
            self.retrieved_at.utc()
            <= self.revalidated_at.utc()
            <= acquisition.timestamps.receipt.utc(),
            "SCHEDULE_CHRONOLOGY_CONFLICT",
        )
        if self.state is ScheduleState.REVISED:
            require(self.predecessor is not None, "REVISION_PREDECESSOR_REQUIRED")
            require(self.predecessor != self.version, "SELF_REFERENCING_REVISION")
            require(predecessor is not None, "REVISION_HISTORY_REQUIRED")
            require(
                self.predecessor_artifact == predecessor,
                "PREDECESSOR_ARTIFACT_BINDING_MISMATCH",
            )
            _validate_schedule_history(predecessor, self.source, set())
            require(
                predecessor.version == self.predecessor
                and predecessor.game_id == self.game_id
                and predecessor.provider_event_id == self.provider_event_id,
                "MALFORMED_PREDECESSOR_CHAIN",
            )
            require(
                predecessor.version != self.version
                and predecessor.kickoff.utc() != self.kickoff.utc(),
                "INVALID_REVISION_CHANGE",
            )
        else:
            require(
                self.predecessor is None
                and self.predecessor_artifact is None
                and predecessor is None,
                "INITIAL_SCHEDULE_HAS_PREDECESSOR",
            )


def _validate_schedule_history(
    artifact: ScheduleVersion,
    expected_source: ExternalClaim,
    seen_versions: set[str],
) -> None:
    require(artifact.version not in seen_versions, "CYCLIC_PREDECESSOR_CHAIN")
    seen_versions.add(artifact.version)
    require(artifact.source_available is True, "INVALID_PREDECESSOR_ARTIFACT")
    require(
        artifact.state in (ScheduleState.SCHEDULED, ScheduleState.REVISED),
        "INVALID_PREDECESSOR_STATE",
    )
    require(artifact.source == expected_source, "PREDECESSOR_SOURCE_MISMATCH")
    artifact.source.require_fixture()
    require(
        len(artifact.source_fingerprint) == 64
        and all(char in "0123456789abcdef" for char in artifact.source_fingerprint),
        "INVALID_PREDECESSOR_FINGERPRINT",
    )
    require(
        artifact.retrieved_at.utc() <= artifact.revalidated_at.utc(),
        "INVALID_PREDECESSOR_CHRONOLOGY",
    )
    if artifact.state is ScheduleState.SCHEDULED:
        require(
            artifact.predecessor is None and artifact.predecessor_artifact is None,
            "MALFORMED_PREDECESSOR_ARTIFACT",
        )
        return
    require(
        artifact.predecessor is not None
        and artifact.predecessor != artifact.version
        and artifact.predecessor_artifact is not None,
        "MALFORMED_PREDECESSOR_ARTIFACT",
    )
    prior = artifact.predecessor_artifact
    require(
        prior.version == artifact.predecessor
        and prior.game_id == artifact.game_id
        and prior.provider_event_id == artifact.provider_event_id,
        "MALFORMED_PREDECESSOR_CHAIN",
    )
    require(prior.kickoff.utc() != artifact.kickoff.utc(), "INVALID_REVISION_CHANGE")
    _validate_schedule_history(prior, expected_source, seen_versions)


class JurisdictionClass(StrEnum):
    UNKNOWN = "UNKNOWN"
    US_AGGREGATE = "US_AGGREGATE"
    US_STATE_SPECIFIC = "US_STATE_SPECIFIC"
    NON_US = "NON_US"
    GLOBAL_UNQUALIFIED = "GLOBAL_UNQUALIFIED"


@dataclass(frozen=True, slots=True)
class ExecutionScopeEvidence(Contract):
    feed_reference: str
    jurisdiction: JurisdictionClass
    state_reference: str
    account_reference: str
    scope: str
    response_id: str
    prices: tuple[int, ...]
    market_available: bool
    restrictions: tuple[str, ...]
    compared_at: Timestamp
    expires_at: Timestamp
    jurisdiction_claim: ExternalClaim
    execution_claim: ExternalClaim

    def validate(
        self,
        acquisition: AcquisitionEnvelope,
        state: str,
        account: str,
        scope: str,
        now: Timestamp,
    ) -> None:
        require(
            self.jurisdiction is JurisdictionClass.US_STATE_SPECIFIC,
            "UNKNOWN_OR_UNAPPROVED_JURISDICTION",
        )
        require(self.state_reference == state, "STATE_MISMATCH")
        require(
            self.account_reference == account and self.scope == scope,
            "ACCOUNT_SCOPE_MISMATCH",
        )
        require(
            self.market_available is True and not self.restrictions,
            "MARKET_UNAVAILABLE_OR_RESTRICTED",
        )
        require(
            self.response_id == acquisition.response_id
            and self.prices == acquisition.draftkings_prices,
            "EXECUTION_PRICE_OR_RESPONSE_MISMATCH",
        )
        require(
            self.compared_at.utc() == acquisition.timestamps.receipt.utc(),
            "COMPARISON_TIME_MISMATCH",
        )
        require(
            self.compared_at.utc() <= now.utc() < self.expires_at.utc(),
            "EXPIRED_EXECUTION_SCOPE",
        )
        require(
            self.jurisdiction_claim.blocker is Blocker.JURISDICTION
            and self.execution_claim.blocker is Blocker.EXECUTION,
            "WRONG_EXECUTION_CLAIMS",
        )
        self.jurisdiction_claim.require_fixture()
        self.execution_claim.require_fixture()


@dataclass(frozen=True, slots=True)
class HistoricalRecord(Contract):
    record_id: str


@dataclass(frozen=True, slots=True)
class PreviewRecord(Contract):
    record_id: str


@dataclass(frozen=True, slots=True)
class ProspectiveFixture(Contract):
    acquisition: AcquisitionEnvelope
    boundary: PathBoundary


def validate_transfer(
    record: HistoricalRecord | PreviewRecord | ProspectiveFixture,
    destination: PathBoundary,
) -> None:
    destination.validate()
    if type(record) is HistoricalRecord:
        require(
            destination.path is DataPath.HISTORICAL, "HISTORICAL_PROMOTION_PROHIBITED"
        )
    elif type(record) is PreviewRecord:
        require(destination.path is DataPath.PREVIEW, "PREVIEW_PROMOTION_PROHIBITED")
    else:
        require(type(record) is ProspectiveFixture, "WRONG_RECORD_TYPE")
        record.boundary.validate()
        require(record.boundary.path is DataPath.PROSPECTIVE, "WRONG_SOURCE_PATH")
        require(
            destination.path in (DataPath.PROSPECTIVE, DataPath.OPERATIONS),
            "BACKWARD_EVIDENCE_FLOW_PROHIBITED",
        )


@dataclass(frozen=True, slots=True)
class ReviewEvidence(Contract):
    synthetic_verification: ReviewClaim
    authorized_conformance: ReviewClaim
    independent_review: ReviewClaim

    def validate(
        self,
        subject: Subject,
        approval: ApprovalEnvelope,
        validation_id: str,
    ) -> None:
        expected = (
            (self.synthetic_verification, ReviewRole.SYNTHETIC_VERIFICATION),
            (self.authorized_conformance, ReviewRole.AUTHORIZED_CONFORMANCE),
            (self.independent_review, ReviewRole.INDEPENDENT_REVIEW),
        )
        dependencies = {claim.blocker: claim for claim in approval.dependencies}
        governance = dependencies.get(Blocker.GOVERNANCE)
        require(governance is not None, "REVIEW_GOVERNANCE_DEPENDENCY_REQUIRED")
        for attestation, role in expected:
            attestation.validate(
                role,
                subject,
                approval.approval_id,
                validation_id,
                governance,
            )
        require(
            len({item.artifact_id for item, _ in expected}) == len(expected),
            "DUPLICATE_REVIEW_ARTIFACT",
        )
        require(
            len({item.claim.reference for item, _ in expected}) == len(expected),
            "DUPLICATE_REVIEW_CLAIM",
        )


class ReviewRole(StrEnum):
    SYNTHETIC_VERIFICATION = "synthetic_verification"
    AUTHORIZED_CONFORMANCE = "authorized_conformance"
    INDEPENDENT_REVIEW = "independent_review"


def expected_review_artifact(role: ReviewRole, subject: Subject) -> str:
    return f"fixture:review-artifact:{role.value}:{subject.implementation_id}"


def expected_review_reference(
    role: ReviewRole,
    subject: Subject,
    approval_id: str,
    validation_id: str,
) -> str:
    return (
        f"fixture:review-claim:{role.value}:{subject.implementation_id}:"
        f"{approval_id}:{validation_id}"
    )


@dataclass(frozen=True, slots=True)
class ReviewClaim(Contract):
    role: ReviewRole
    subject: Subject
    artifact_id: str
    claim: ExternalClaim
    governance_dependency: ExternalClaim

    def validate(
        self,
        expected_role: ReviewRole,
        expected_subject: Subject,
        approval_id: str,
        validation_id: str,
        governance_dependency: ExternalClaim,
    ) -> None:
        require(self.role is expected_role, "WRONG_REVIEW_ROLE")
        require(self.subject == expected_subject, "REVIEW_SUBJECT_MISMATCH")
        require(
            self.artifact_id == expected_review_artifact(expected_role, expected_subject),
            "REVIEW_ARTIFACT_MISMATCH",
        )
        require(self.claim.blocker is Blocker.GOVERNANCE, "WRONG_REVIEW_CLAIM")
        self.claim.require_fixture()
        require(
            self.claim.reference
            == expected_review_reference(
                expected_role,
                expected_subject,
                approval_id,
                validation_id,
            ),
            "REVIEW_CONTEXT_MISMATCH",
        )
        require(
            self.governance_dependency == governance_dependency,
            "REVIEW_GOVERNANCE_MISMATCH",
        )


@dataclass(frozen=True, slots=True)
class GateResult(Contract):
    fixture_conditions_satisfied: bool
    reasons: tuple[str, ...]
    game_id: str | None = None
    response_id: str | None = None
    approval_id: str | None = None
    validation_id: str | None = None
    context_binding: str | None = None

    @property
    def real_evidence_write_allowed(self) -> bool:
        return False

    @property
    def external_claims_authenticated(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class ActivationContext(Contract):
    record: ProspectiveFixture
    approval: ApprovalEnvelope | None
    expected: Subject
    scope: str
    state_reference: str
    account_reference: str
    schedule: ScheduleVersion
    execution: ExecutionScopeEvidence
    retention: RetentionContract
    reviews: ReviewEvidence
    now: Timestamp
    validation_id: str
    finalization_id: str
    schedule_predecessor: ScheduleVersion | None = None
    accepted_game_ids: tuple[str, ...] = ()
    accepted_response_ids: tuple[str, ...] = ()

    def evaluate(self) -> GateResult:
        return simulate_activation_gate(
            self.record,
            self.approval,
            self.expected,
            self.scope,
            self.state_reference,
            self.account_reference,
            self.schedule,
            self.execution,
            self.retention,
            self.reviews,
            self.now,
            validation_id=self.validation_id,
            finalization_id=self.finalization_id,
            schedule_predecessor=self.schedule_predecessor,
            accepted_game_ids=self.accepted_game_ids,
            accepted_response_ids=self.accepted_response_ids,
        )


@dataclass(frozen=True, slots=True)
class FinalizationAuthorization(Contract):
    finalization_id: str
    approval: ApprovalEnvelope
    subject: Subject
    scope: str
    game_id: str
    response_id: str
    provenance_reference: str
    provenance_claim: ExternalClaim

    def validate(
        self,
        expected_subject: Subject,
        expected_scope: str,
        expected_game_id: str,
        expected_response_id: str,
        expected_finalization_id: str,
        now: Timestamp,
    ) -> None:
        require(
            self.finalization_id == expected_finalization_id,
            "FINALIZATION_IDENTITY_MISMATCH",
        )
        require(self.subject == expected_subject, "FINALIZATION_SUBJECT_MISMATCH")
        require(self.scope == expected_scope, "FINALIZATION_SCOPE_MISMATCH")
        require(
            self.game_id == expected_game_id
            and self.response_id == expected_response_id,
            "FINALIZATION_CAPTURE_MISMATCH",
        )
        self.approval.validate(self.subject, self.scope, Action.FINALIZE, now)
        require(
            self.provenance_reference
            == f"fixture:finalization-provenance:{self.finalization_id}",
            "FINALIZATION_PROVENANCE_REQUIRED",
        )
        require(
            self.provenance_claim.blocker is Blocker.GOVERNANCE,
            "WRONG_FINALIZATION_PROVENANCE",
        )
        self.provenance_claim.require_fixture()
        dependencies = {claim.blocker: claim for claim in self.approval.dependencies}
        require(
            self.provenance_claim == dependencies.get(Blocker.GOVERNANCE),
            "FINALIZATION_PROVENANCE_MISMATCH",
        )


def simulate_activation_gate(
    record: ProspectiveFixture,
    approval: ApprovalEnvelope | None,
    expected: Subject,
    scope: str,
    state_reference: str,
    account_reference: str,
    schedule: ScheduleVersion,
    execution: ExecutionScopeEvidence,
    retention: RetentionContract,
    reviews: ReviewEvidence,
    now: Timestamp,
    *,
    validation_id: str = "fixture:activation-validation",
    finalization_id: str = "fixture:finalization:accepted-result",
    schedule_predecessor: ScheduleVersion | None = None,
    accepted_game_ids: tuple[str, ...] = (),
    accepted_response_ids: tuple[str, ...] = (),
) -> GateResult:
    """Exercise proposed gates in memory; even a successful fixture denies real writes."""
    try:
        require(
            type(record) is ProspectiveFixture, "HISTORICAL_OR_PREVIEW_NOT_EVIDENCE"
        )
        validate_transfer(record, record.boundary)
        require(record.boundary.path is DataPath.PROSPECTIVE, "WRONG_DESTINATION")
        require(type(approval) is ApprovalEnvelope, "MISSING_AUTHORIZATION")
        approval.validate(expected, scope, Action.EVIDENCE, now)
        acquisition = record.acquisition
        require(
            acquisition.timestamps.effective_authorization.utc()
            == approval.effective_at.utc(),
            "WRONG_EFFECTIVE_TIME",
        )
        acquisition.validate()
        require(
            acquisition.timestamps.receipt.utc()
            <= now.utc()
            < acquisition.timestamps.kickoff.utc(),
            "INVALID_COMMIT_TIME",
        )
        require(validation_id.startswith("fixture:"), "VALIDATION_ID_REQUIRED")
        require(
            finalization_id.startswith("fixture:finalization:"),
            "FINALIZATION_ID_REQUIRED",
        )
        schedule.validate(acquisition, schedule_predecessor)
        execution.validate(acquisition, state_reference, account_reference, scope, now)
        retention.validate(now)
        require(
            acquisition.permission_mode is retention.mode is RetentionMode.QUALIFYING,
            "EVIDENCE_RETENTION_NOT_PERMITTED",
        )
        reviews.validate(expected, approval, validation_id)
        dependencies = {claim.blocker: claim for claim in approval.dependencies}
        for claim in (
            acquisition.provider_claim,
            acquisition.timestamps.semantics,
            schedule.source,
            execution.jurisdiction_claim,
            execution.execution_claim,
            retention.permission,
        ):
            require(
                claim == dependencies.get(claim.blocker), "DEPENDENCY_BINDING_MISMATCH"
            )
        require(
            acquisition.game_id not in accepted_game_ids,
            "LATER_PRICE_REPLACEMENT_PROHIBITED",
        )
        require(
            acquisition.response_id not in accepted_response_ids, "REPLAYED_ACCEPTANCE"
        )
    except ContractError as exc:
        return GateResult(False, (str(exc),))
    context = ActivationContext(
        record,
        approval,
        expected,
        scope,
        state_reference,
        account_reference,
        schedule,
        execution,
        retention,
        reviews,
        now,
        validation_id,
        finalization_id,
        schedule_predecessor,
        accepted_game_ids,
        accepted_response_ids,
    )
    return GateResult(
        True,
        (),
        acquisition.game_id,
        acquisition.response_id,
        approval.approval_id,
        validation_id,
        structural_digest(context),
    )


class FailureClass(StrEnum):
    TIMEOUT = "TIMEOUT"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"
    RETRY = "RETRY"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"
    CLOCK_DISAGREEMENT = "CLOCK_DISAGREEMENT"
    APPROVAL_EXPIRY = "APPROVAL_EXPIRY"
    PERMISSION_EXPIRY = "PERMISSION_EXPIRY"
    INTERRUPTED_COMMIT = "INTERRUPTED_COMMIT"


@dataclass(frozen=True, slots=True)
class OperationalFailure(Contract):
    kind: FailureClass
    attempt_id: str
    policy_reference: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalPolicy(Contract):
    """No production numbers. Tests may supply a separately labelled fixture policy."""

    timeout_seconds: int | None = None
    retry_limit: int | None = None
    backoff_seconds: tuple[int, ...] | None = None
    fixture_policy_reference: str | None = None

    def require_fixture(self) -> None:
        require(
            self.fixture_policy_reference is not None
            and self.fixture_policy_reference.startswith("fixture:"),
            "REQUIRED_POLICY_UNSET",
        )
        require(
            self.timeout_seconds is not None and self.timeout_seconds > 0,
            "REQUIRED_TIMEOUT_POLICY",
        )
        require(
            self.retry_limit is not None and self.retry_limit >= 0,
            "REQUIRED_RETRY_POLICY",
        )
        require(
            self.backoff_seconds is not None
            and len(self.backoff_seconds) == self.retry_limit
            and all(delay >= 0 for delay in self.backoff_seconds),
            "REQUIRED_BACKOFF_POLICY",
        )
