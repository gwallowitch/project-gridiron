"""Pure, synthetic-only integration of inactive Core-Three contracts.

This module has no I/O and establishes no external fact. It composes existing
schedule, acquisition, market, authority, and lifecycle structures so their local
relationships can be validated without creating prospective evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from gridiron.market.core_three_consensus import (
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
    build_consensus_preview,
)
from gridiron.market.core_three_types import (
    CANDIDATE_ID,
    CANDIDATE_VARIANT_ID,
    EXECUTION_BOOK_KEY,
    PROTOCOL_ID,
    AtomicObservation,
    Book,
    CoreThreeError,
    Market,
    Outcome,
)
from gridiron.market.moneyline import american_odds_to_implied_probability
from gridiron.market.synthetic_contracts import (
    AcquisitionEnvelope,
    ActivationContext,
    Blocker,
    ContractError,
    DataPath,
    FailureClass,
    RetentionMode,
    ScheduleState,
    ScheduleVersion,
)

ELIGIBILITY = "strictly_positive_edge"
VALIDATION_ORDER = (
    "protocol_path_separation",
    "schedule_identity",
    "schedule_ancestry",
    "provider_claim",
    "response_identity",
    "response_fingerprint",
    "timestamp_representation",
    "timestamp_semantics_dependency",
    "jurisdiction",
    "execution_scope",
    "market_completeness",
    "same_response_atomicity",
    "core_three_consensus",
    "frozen_candidate_inputs",
    "candidate_probability",
    "offered_price",
    "break_even_probability",
    "edge",
    "mathematical_decision",
    "authority_dependencies",
    "lifecycle_replay_binding",
)
MAX_QUOTE_AGE = timedelta(minutes=10)


class IntegrationError(ValueError):
    """Raised when a synthetic integration invariant is violated."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise IntegrationError(reason)


def canonical_digest(value: object) -> str:
    """Return a deterministic structural digest; never external authentication."""

    def canonical(item: object) -> object:
        if isinstance(item, StrEnum):
            return {"type": type(item).__qualname__, "value": item.value}
        if isinstance(item, datetime):
            require(
                item.tzinfo is not None and item.utcoffset() is not None,
                "NAIVE_DATETIME_IN_BINDING",
            )
            return item.astimezone(UTC).isoformat()
        if hasattr(type(item), "__dataclass_fields__"):
            return {
                "type": type(item).__qualname__,
                "fields": [
                    [field.name, canonical(getattr(item, field.name))]
                    for field in fields(item)
                ],
            }
        if isinstance(item, tuple):
            return {"type": "tuple", "items": [canonical(value) for value in item]}
        if isinstance(item, dict):
            return {
                "type": "dict",
                "items": [
                    [str(key), canonical(item[key])]
                    for key in sorted(item, key=lambda part: str(part))
                ],
            }
        if type(item) is float:
            require(math.isfinite(item), "NONFINITE_VALUE_IN_BINDING")
            return {"type": "float", "value": item.hex()}
        if item is None or type(item) in (bool, int, str):
            return item
        raise IntegrationError("UNSUPPORTED_BINDING_TYPE")

    encoded = json.dumps(
        canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuthorityKind(StrEnum):
    PROVIDER_AUTHENTICATION = "provider_authentication"
    TIMESTAMP_AUTHORITY = "timestamp_authority"
    JURISDICTION_AUTHORITY = "jurisdiction_authority"
    EXECUTION_AUTHORITY = "execution_authority"
    RETENTION_AUTHORITY = "retention_authority"
    SCHEDULE_AUTHORITY = "schedule_authority"
    GOVERNANCE_AUTHORITY = "governance_authority"
    EFFECTIVE_TIME_AUTHORITY = "effective_time_authority"


class AuthorityState(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


@dataclass(frozen=True, slots=True)
class AuthorityDependency:
    kind: AuthorityKind
    subject_binding: str
    context_binding: str
    approval_id: str
    validation_id: str
    artifact_id: str
    state: AuthorityState

    def validate(
        self,
        subject_binding: str,
        context_binding: str,
        approval_id: str,
        validation_id: str,
    ) -> None:
        require(self.subject_binding == subject_binding, "AUTHORITY_SUBJECT_MISMATCH")
        require(self.context_binding == context_binding, "AUTHORITY_CONTEXT_MISMATCH")
        require(self.approval_id == approval_id, "AUTHORITY_APPROVAL_MISMATCH")
        require(self.validation_id == validation_id, "AUTHORITY_VALIDATION_MISMATCH")
        require(
            self.artifact_id
            == expected_authority_artifact(
                self.kind,
                subject_binding,
                context_binding,
                approval_id,
                validation_id,
            ),
            "AUTHORITY_ARTIFACT_MISMATCH",
        )
        require(
            self.state is AuthorityState.SYNTHETIC_FIXTURE,
            "AUTHORITY_DEPENDENCY_UNRESOLVED",
        )


def expected_authority_artifact(
    kind: AuthorityKind,
    subject_binding: str,
    context_binding: str,
    approval_id: str,
    validation_id: str,
) -> str:
    identity = canonical_digest(
        (kind, subject_binding, context_binding, approval_id, validation_id)
    )
    return f"fixture:integration-authority:{kind.value}:{identity}"


def synthetic_authority_dependencies(
    subject_binding: str,
    context_binding: str,
    approval_id: str,
    validation_id: str,
) -> tuple[AuthorityDependency, ...]:
    return tuple(
        AuthorityDependency(
            kind,
            subject_binding,
            context_binding,
            approval_id,
            validation_id,
            expected_authority_artifact(
                kind,
                subject_binding,
                context_binding,
                approval_id,
                validation_id,
            ),
            AuthorityState.SYNTHETIC_FIXTURE,
        )
        for kind in AuthorityKind
    )


@dataclass(frozen=True, slots=True)
class FrozenCandidateContract:
    candidate_id: str = CANDIDATE_ID
    candidate_variant_id: str = CANDIDATE_VARIANT_ID
    market_coefficient: float = MARKET_COEFFICIENT
    def_epa_coefficient: float = DEF_EPA_COEFFICIENT
    intercept: float = INTERCEPT
    residual_cap: float = RESIDUAL_CAP
    eligibility: str = ELIGIBILITY

    def validate(self) -> None:
        require(self.candidate_id == CANDIDATE_ID, "CANDIDATE_IDENTITY_CHANGED")
        require(
            self.candidate_variant_id == CANDIDATE_VARIANT_ID,
            "CANDIDATE_VARIANT_CHANGED",
        )
        require(self.market_coefficient == MARKET_COEFFICIENT, "MARKET_COEFFICIENT_CHANGED")
        require(
            self.def_epa_coefficient == DEF_EPA_COEFFICIENT,
            "DEF_EPA_COEFFICIENT_CHANGED",
        )
        require(self.intercept == INTERCEPT, "INTERCEPT_CHANGED")
        require(self.residual_cap == RESIDUAL_CAP, "RESIDUAL_CAP_CHANGED")
        require(self.eligibility == ELIGIBILITY, "ELIGIBILITY_CHANGED")


class DefEpaState(StrEnum):
    OBSERVED = "OBSERVED"
    WEEK_ONE_NEUTRAL = "WEEK_ONE_NEUTRAL"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class DefEpaInput:
    value: float | None
    source_id: str
    vintage_id: str
    state: DefEpaState

    def validated_value(self, week: int) -> float:
        require(self.source_id.startswith("fixture:"), "DEF_EPA_SOURCE_REQUIRED")
        require(self.vintage_id.startswith("fixture:"), "DEF_EPA_VINTAGE_REQUIRED")
        if self.state is DefEpaState.WEEK_ONE_NEUTRAL:
            require(week == 1 and self.value is None, "INVALID_WEEK_ONE_MISSINGNESS")
            return 0.0
        require(self.state is DefEpaState.OBSERVED, "DEF_EPA_MISSING")
        require(
            type(self.value) is float and math.isfinite(self.value),
            "INVALID_DEF_EPA",
        )
        return self.value


class AttemptKind(StrEnum):
    INITIAL = "INITIAL"
    RETRY_AFTER_REJECTION = "RETRY_AFTER_REJECTION"
    RETRY_AFTER_TIMEOUT = "RETRY_AFTER_TIMEOUT"
    RESTART_AFTER_SCHEDULE_REVISION = "RESTART_AFTER_SCHEDULE_REVISION"
    VOID_AFTER_SCHEDULE_REVISION = "VOID_AFTER_SCHEDULE_REVISION"
    SUPERSEDE_AFTER_SCHEDULE_REVISION = "SUPERSEDE_AFTER_SCHEDULE_REVISION"


class AttemptState(StrEnum):
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"
    ACCEPTED = "ACCEPTED"
    VOIDED = "VOIDED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    attempt_id: str
    request_id: str
    response_id: str | None
    schedule_version: str
    kind: AttemptKind
    state: AttemptState
    predecessor_attempt_id: str | None = None
    failure: FailureClass | None = None
    schedule_artifact_binding: str = "0" * 64


@dataclass(frozen=True, slots=True)
class AttemptHistory:
    attempts: tuple[AttemptRecord, ...]

    def validate(self) -> None:
        require(bool(self.attempts), "ATTEMPT_HISTORY_REQUIRED")
        attempt_ids: set[str] = set()
        request_ids: set[str] = set()
        accepted_responses: set[str] = set()
        seen_responses: set[str] = set()
        by_id: dict[str, AttemptRecord] = {}
        accepted = False
        voided = False
        for index, attempt in enumerate(self.attempts):
            require(attempt.attempt_id not in attempt_ids, "DUPLICATE_ATTEMPT")
            require(attempt.request_id not in request_ids, "DUPLICATE_REQUEST")
            require(
                len(attempt.schedule_artifact_binding) == 64
                and all(
                    character in "0123456789abcdef"
                    for character in attempt.schedule_artifact_binding
                ),
                "INVALID_ATTEMPT_SCHEDULE_BINDING",
            )
            attempt_ids.add(attempt.attempt_id)
            request_ids.add(attempt.request_id)
            if attempt.response_id is not None:
                require(attempt.response_id not in seen_responses, "DUPLICATE_RESPONSE")
                seen_responses.add(attempt.response_id)
            require(not voided, "VOIDED_OBSERVATION_TERMINAL")
            if accepted:
                require(
                    attempt.kind is AttemptKind.VOID_AFTER_SCHEDULE_REVISION,
                    "ACCEPTED_OBSERVATION_IMMUTABLE",
                )
            if index == 0:
                require(
                    attempt.kind is AttemptKind.INITIAL
                    and attempt.predecessor_attempt_id is None,
                    "INITIAL_ATTEMPT_REQUIRED",
                )
            else:
                prior = by_id.get(attempt.predecessor_attempt_id)
                require(prior is not None, "RETRY_PREDECESSOR_REQUIRED")
                require(
                    attempt.predecessor_attempt_id
                    == self.attempts[index - 1].attempt_id,
                    "NONLINEAR_ATTEMPT_CHAIN",
                )
                if attempt.kind is AttemptKind.RETRY_AFTER_REJECTION:
                    require(prior.state is AttemptState.REJECTED, "RETRY_REQUIRES_REJECTION")
                    require(
                        prior.schedule_version == attempt.schedule_version,
                        "RETRY_SCHEDULE_CHANGED",
                    )
                elif attempt.kind is AttemptKind.RETRY_AFTER_TIMEOUT:
                    require(prior.state is AttemptState.TIMED_OUT, "RETRY_REQUIRES_TIMEOUT")
                    require(
                        prior.schedule_version == attempt.schedule_version,
                        "RETRY_SCHEDULE_CHANGED",
                    )
                elif attempt.kind is AttemptKind.RESTART_AFTER_SCHEDULE_REVISION:
                    require(
                        prior.state
                        in (
                            AttemptState.REJECTED,
                            AttemptState.TIMED_OUT,
                            AttemptState.SUPERSEDED,
                        ),
                        "REVISION_RESTART_REQUIRES_FAILED_ATTEMPT",
                    )
                    if prior.state is AttemptState.SUPERSEDED:
                        require(
                            prior.schedule_version == attempt.schedule_version,
                            "REVISION_RESTART_SCHEDULE_MISMATCH",
                        )
                    else:
                        require(
                            prior.schedule_version != attempt.schedule_version,
                            "REVISION_RESTART_REQUIRES_NEW_SCHEDULE",
                        )
                elif attempt.kind is AttemptKind.VOID_AFTER_SCHEDULE_REVISION:
                    require(prior.state is AttemptState.ACCEPTED, "VOID_REQUIRES_ACCEPTED_ATTEMPT")
                    require(
                        prior.schedule_version != attempt.schedule_version,
                        "VOID_REQUIRES_NEW_SCHEDULE",
                    )
                elif attempt.kind is AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION:
                    require(
                        prior.state is AttemptState.PENDING,
                        "SUPERSESSION_REQUIRES_PENDING_ATTEMPT",
                    )
                    require(
                        prior.schedule_version != attempt.schedule_version,
                        "SUPERSESSION_REQUIRES_NEW_SCHEDULE",
                    )
                else:
                    raise IntegrationError("INVALID_RETRY_KIND")
            if attempt.state is AttemptState.PENDING:
                if index != len(self.attempts) - 1:
                    successor = self.attempts[index + 1]
                    require(
                        successor.kind
                        is AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
                        "PENDING_ATTEMPT_NOT_CURRENT",
                    )
                require(attempt.response_id is not None, "PENDING_RESPONSE_ID_REQUIRED")
                require(attempt.failure is None, "PENDING_ATTEMPT_HAS_FAILURE")
            elif attempt.state is AttemptState.REJECTED:
                require(attempt.failure is not None, "REJECTION_REASON_REQUIRED")
            elif attempt.state is AttemptState.TIMED_OUT:
                require(attempt.failure is FailureClass.TIMEOUT, "TIMEOUT_REASON_REQUIRED")
                require(attempt.response_id is None, "TIMEOUT_HAS_RESPONSE")
            elif attempt.state is AttemptState.ACCEPTED:
                require(attempt.response_id is not None, "ACCEPTED_RESPONSE_REQUIRED")
                require(attempt.response_id not in accepted_responses, "REPLAYED_RESPONSE")
                accepted_responses.add(attempt.response_id)
                accepted = True
            elif attempt.state is AttemptState.SUPERSEDED:
                require(
                    attempt.kind is AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
                    "INVALID_SUPERSESSION",
                )
                require(attempt.response_id is None, "SUPERSESSION_HAS_RESPONSE")
                require(
                    attempt.failure is FailureClass.SCHEDULE_CONFLICT,
                    "SUPERSESSION_REASON_REQUIRED",
                )
            else:
                require(attempt.state is AttemptState.VOIDED, "UNKNOWN_ATTEMPT_STATE")
                require(accepted, "VOID_REQUIRES_ACCEPTED_ATTEMPT")
                require(attempt.response_id is None, "VOID_HAS_RESPONSE")
                require(
                    attempt.failure is FailureClass.SCHEDULE_CONFLICT,
                    "VOID_REASON_REQUIRED",
                )
                voided = True
            by_id[attempt.attempt_id] = attempt

    @property
    def current(self) -> AttemptRecord:
        self.validate()
        return self.attempts[-1]

    @property
    def timeout_policy_externally_established(self) -> bool:
        return False


class DecisionState(StrEnum):
    REJECTED = "REJECTED"
    NO_BET = "NO_BET"
    POSITIVE_EDGE_CANDIDATE = "POSITIVE_EDGE_CANDIDATE"


@dataclass(frozen=True, slots=True)
class SyntheticOperationalTransaction:
    activation: ActivationContext
    observation: AtomicObservation
    candidate: FrozenCandidateContract
    def_epa: DefEpaInput
    season: int
    season_type: str
    week: int
    authorities: tuple[AuthorityDependency, ...]
    attempts: AttemptHistory

    def validate(self) -> None:
        require(type(self.activation) is ActivationContext, "ACTIVATION_CONTEXT_REQUIRED")
        require(type(self.observation) is AtomicObservation, "OBSERVATION_REQUIRED")
        require(type(self.candidate) is FrozenCandidateContract, "CANDIDATE_REQUIRED")
        require(type(self.attempts) is AttemptHistory, "ATTEMPT_HISTORY_REQUIRED")
        require(self.activation.record.boundary.path is DataPath.PROSPECTIVE, "WRONG_PATH")
        require(self.activation.expected.protocol_id == PROTOCOL_ID, "WRONG_PROTOCOL")
        require(self.observation.protocol_id == PROTOCOL_ID, "WRONG_OBSERVATION_PROTOCOL")
        require(self.season == 2026 and self.season_type == "REG", "WRONG_POPULATION")
        require(type(self.week) is int and 1 <= self.week <= 16, "WRONG_POPULATION_WEEK")
        self.candidate.validate()
        acquisition = self.activation.record.acquisition
        schedule = self.activation.schedule
        require(type(schedule) is ScheduleVersion, "SCHEDULE_REQUIRED")
        require(schedule.state in (ScheduleState.SCHEDULED, ScheduleState.REVISED), "SCHEDULE_NOT_CAPTURABLE")
        require(
            acquisition.game_id
            == schedule.game_id
            == self.observation.authoritative_game_id,
            "GAME_IDENTITY_MISMATCH",
        )
        require(
            acquisition.provider_event_id
            == schedule.provider_event_id
            == self.observation.provider_event_id,
            "PROVIDER_EVENT_IDENTITY_MISMATCH",
        )
        require(
            acquisition.response_id == self.observation.response_id,
            "RESPONSE_IDENTITY_MISMATCH",
        )
        require(
            acquisition.provenance_fingerprint == self.observation.response_digest,
            "RESPONSE_FINGERPRINT_MISMATCH",
        )
        require(self.observation.provider == "The Odds API", "PROVIDER_IDENTITY_MISMATCH")
        require(
            acquisition.timestamps.receipt.utc() == self.observation.receipt_at,
            "RECEIPT_TIMESTAMP_MISMATCH",
        )
        require(
            acquisition.timestamps.kickoff.utc()
            == schedule.kickoff.utc()
            == self.observation.kickoff_at,
            "KICKOFF_MISMATCH",
        )
        self.observation.validate()
        _validate_core_three_market_contents(self.observation)
        gate = self.activation.evaluate()
        require(gate.fixture_conditions_satisfied, "SYNTHETIC_ACTIVATION_GATE_REJECTED")
        require(not gate.reasons, "SYNTHETIC_ACTIVATION_GATE_REJECTED")
        draftkings = self.observation.book(EXECUTION_BOOK_KEY).market("h2h")
        by_name = {outcome.name: outcome.price for outcome in draftkings.outcomes}
        prices = (
            by_name[self.observation.home_team],
            by_name[self.observation.away_team],
        )
        require(prices == acquisition.draftkings_prices, "ACQUISITION_PRICE_MISMATCH")
        require(prices == self.activation.execution.prices, "EXECUTION_PRICE_MISMATCH")
        require(
            acquisition.permission_mode
            is self.activation.retention.mode
            is RetentionMode.QUALIFYING,
            "RETENTION_MODE_MISMATCH",
        )
        subject_binding = canonical_digest(self.activation.expected)
        context_binding = transaction_authority_context_binding(self)
        approval = self.activation.approval
        require(approval is not None, "APPROVAL_REQUIRED")
        require(len(self.authorities) == len(AuthorityKind), "MISSING_AUTHORITIES")
        require(
            {dependency.kind for dependency in self.authorities} == set(AuthorityKind),
            "DUPLICATE_OR_WRONG_AUTHORITY",
        )
        for dependency in self.authorities:
            dependency.validate(
                subject_binding,
                context_binding,
                approval.approval_id,
                self.activation.validation_id,
            )
        blocker_map = {
            AuthorityKind.PROVIDER_AUTHENTICATION: Blocker.PROVIDER,
            AuthorityKind.TIMESTAMP_AUTHORITY: Blocker.SEMANTICS,
            AuthorityKind.JURISDICTION_AUTHORITY: Blocker.JURISDICTION,
            AuthorityKind.EXECUTION_AUTHORITY: Blocker.EXECUTION,
            AuthorityKind.RETENTION_AUTHORITY: Blocker.PERMISSION,
            AuthorityKind.SCHEDULE_AUTHORITY: Blocker.SCHEDULE,
            AuthorityKind.GOVERNANCE_AUTHORITY: Blocker.GOVERNANCE,
            AuthorityKind.EFFECTIVE_TIME_AUTHORITY: Blocker.EFFECTIVE,
        }
        approval_dependencies = {item.blocker for item in approval.dependencies}
        require(
            {blocker_map[item.kind] for item in self.authorities}
            == approval_dependencies,
            "AUTHORITY_DEPENDENCY_SET_MISMATCH",
        )
        self.attempts.validate()
        _validate_attempt_schedule_consistency(
            self.attempts, self.activation, acquisition
        )
        current = self.attempts.current
        require(current.state is AttemptState.PENDING, "CURRENT_ATTEMPT_NOT_PENDING")
        require(current.attempt_id == acquisition.attempt_id, "ATTEMPT_IDENTITY_MISMATCH")
        require(current.request_id == acquisition.request_id, "REQUEST_IDENTITY_MISMATCH")
        require(current.response_id == acquisition.response_id, "ATTEMPT_RESPONSE_MISMATCH")
        require(current.schedule_version == schedule.version, "ATTEMPT_SCHEDULE_MISMATCH")
        self.def_epa.validated_value(self.week)

    @property
    def binding(self) -> str:
        self.validate()
        return canonical_digest(self)


def transaction_authority_context_binding(
    transaction: SyntheticOperationalTransaction,
) -> str:
    """Bind authorities to all non-authority transaction inputs."""
    return canonical_digest(
        (
            transaction.activation,
            transaction.observation,
            transaction.candidate,
            transaction.def_epa,
            transaction.season,
            transaction.season_type,
            transaction.week,
            transaction.attempts,
        )
    )


def _validate_attempt_schedule_consistency(
    history: AttemptHistory,
    activation: ActivationContext,
    acquisition: AcquisitionEnvelope,
) -> None:
    """Bind revision-related attempts to the actual validated schedule chain."""
    revision_kinds = {
        AttemptKind.RESTART_AFTER_SCHEDULE_REVISION,
        AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION,
        AttemptKind.VOID_AFTER_SCHEDULE_REVISION,
    }
    schedule = activation.schedule
    predecessor = activation.schedule_predecessor
    has_revision_attempt = any(
        attempt.kind in revision_kinds for attempt in history.attempts
    )
    if has_revision_attempt:
        require(
            schedule.state is ScheduleState.REVISED,
            "ATTEMPT_REVISION_REQUIRES_REVISED_SCHEDULE",
        )
        require(predecessor is not None, "ATTEMPT_REVISION_PREDECESSOR_REQUIRED")
        require(
            schedule.predecessor_artifact == predecessor,
            "ATTEMPT_REVISION_PREDECESSOR_ARTIFACT_MISMATCH",
        )
    schedule.validate(acquisition, predecessor)

    schedules: dict[str, ScheduleVersion] = {}
    cursor: ScheduleVersion | None = schedule
    while cursor is not None:
        require(cursor.version not in schedules, "CYCLIC_ATTEMPT_SCHEDULE_CHAIN")
        require(
            cursor.game_id == schedule.game_id == acquisition.game_id,
            "ATTEMPT_SCHEDULE_GAME_MISMATCH",
        )
        require(
            cursor.provider_event_id
            == schedule.provider_event_id
            == acquisition.provider_event_id,
            "ATTEMPT_SCHEDULE_EVENT_MISMATCH",
        )
        schedules[cursor.version] = cursor
        if cursor.state is ScheduleState.SCHEDULED:
            require(
                cursor.predecessor is None and cursor.predecessor_artifact is None,
                "MALFORMED_ATTEMPT_SCHEDULE_ROOT",
            )
            break
        require(cursor.state is ScheduleState.REVISED, "INVALID_ATTEMPT_SCHEDULE_STATE")
        require(
            cursor.predecessor is not None
            and cursor.predecessor_artifact is not None
            and cursor.predecessor_artifact.version == cursor.predecessor,
            "BROKEN_ATTEMPT_SCHEDULE_CHAIN",
        )
        cursor = cursor.predecessor_artifact

    for index, attempt in enumerate(history.attempts):
        attempt_schedule = schedules.get(attempt.schedule_version)
        require(attempt_schedule is not None, "ATTEMPT_SCHEDULE_VERSION_NOT_IN_CHAIN")
        require(
            attempt.schedule_artifact_binding == canonical_digest(attempt_schedule),
            "ATTEMPT_SCHEDULE_ARTIFACT_BINDING_MISMATCH",
        )
        if attempt.kind not in revision_kinds:
            continue
        prior = history.attempts[index - 1]
        revised = attempt_schedule
        require(revised.state is ScheduleState.REVISED, "ATTEMPT_TARGET_NOT_REVISED")
        if attempt.kind is AttemptKind.SUPERSEDE_AFTER_SCHEDULE_REVISION:
            require(
                revised.predecessor == prior.schedule_version,
                "SUPERSEDED_ATTEMPT_PREDECESSOR_MISMATCH",
            )
        elif attempt.kind is AttemptKind.RESTART_AFTER_SCHEDULE_REVISION:
            if prior.state is AttemptState.SUPERSEDED:
                require(
                    attempt.schedule_version == prior.schedule_version,
                    "RESTART_SUPERSESSION_VERSION_MISMATCH",
                )
            else:
                require(
                    revised.predecessor == prior.schedule_version,
                    "RESTART_PREDECESSOR_VERSION_MISMATCH",
                )
        else:
            require(
                revised.predecessor == prior.schedule_version,
                "VOID_PREDECESSOR_VERSION_MISMATCH",
            )


def _validate_core_three_market_contents(observation: AtomicObservation) -> None:
    """Recheck normalized market invariants at the integration trust boundary."""
    require(
        bool(observation.home_team)
        and bool(observation.away_team)
        and observation.home_team != observation.away_team,
        "INVALID_TEAM_IDENTITY",
    )
    for book in observation.books:
        require(type(book) is Book, "INVALID_BOOK_OBJECT")
        require(book.sid is None or (type(book.sid) is str and bool(book.sid)), "INVALID_BOOK_SID")
        for market in book.markets:
            require(type(market) is Market, "INVALID_MARKET_OBJECT")
            require(
                market.last_update <= observation.receipt_at
                and observation.receipt_at - market.last_update <= MAX_QUOTE_AGE,
                "INVALID_MARKET_TIMESTAMP",
            )
            require(len(market.outcomes) == 2, "INCOMPLETE_OUTCOMES")
            require(
                all(type(outcome) is Outcome for outcome in market.outcomes),
                "INVALID_OUTCOME_OBJECT",
            )
            names = tuple(outcome.name for outcome in market.outcomes)
            require(len(set(names)) == 2, "DUPLICATE_OUTCOME")
            for outcome in market.outcomes:
                require(bool(outcome.name), "INVALID_OUTCOME_NAME")
                require(
                    type(outcome.price) is int
                    and not -100 < outcome.price < 100,
                    "MALFORMED_PRICE",
                )
                require(
                    outcome.point is None
                    or (type(outcome.point) is float and math.isfinite(outcome.point)),
                    "MALFORMED_POINT",
                )
                require(
                    outcome.sid is None
                    or (type(outcome.sid) is str and bool(outcome.sid)),
                    "INVALID_OUTCOME_SID",
                )
            if market.key in {"h2h", "spreads"}:
                require(
                    set(names) == {observation.home_team, observation.away_team},
                    "TEAM_OUTCOME_MISMATCH",
                )
            if market.key == "h2h":
                require(
                    all(outcome.point is None for outcome in market.outcomes),
                    "UNEXPECTED_MONEYLINE_POINT",
                )
            elif market.key == "spreads":
                points = tuple(outcome.point for outcome in market.outcomes)
                require(
                    all(point is not None for point in points)
                    and points[0] == -points[1],
                    "CONFLICTING_SPREAD",
                )
            else:
                require(market.key == "totals", "UNKNOWN_MARKET")
                require(set(names) == {"Over", "Under"}, "TOTAL_OUTCOME_MISMATCH")
                points = tuple(outcome.point for outcome in market.outcomes)
                require(
                    all(point is not None for point in points)
                    and points[0] == points[1],
                    "CONFLICTING_TOTAL",
                )


@dataclass(frozen=True, slots=True)
class SyntheticDecisionRecord:
    transaction: SyntheticOperationalTransaction
    transaction_binding: str
    replay_identity: str
    market_consensus_home_probability: float
    def_epa_value: float
    candidate_home_probability: float
    residual_adjustment: float
    selected_side: str
    offered_price: int
    break_even_probability: float
    edge: float
    decision: DecisionState
    validation_order: tuple[str, ...]
    validation_failures: tuple[str, ...]

    def __post_init__(self) -> None:
        expected = _decision_values(self.transaction)
        require(self.transaction_binding == self.transaction.binding, "TRANSACTION_BINDING_MISMATCH")
        require(
            self.replay_identity
            == canonical_digest(
                (
                    self.transaction.attempts.current.attempt_id,
                    self.transaction.observation.response_id,
                    self.transaction.activation.schedule.version,
                    self.transaction_binding,
                )
            ),
            "REPLAY_IDENTITY_MISMATCH",
        )
        require(
            (
                self.market_consensus_home_probability,
                self.def_epa_value,
                self.candidate_home_probability,
                self.residual_adjustment,
                self.selected_side,
                self.offered_price,
                self.break_even_probability,
                self.edge,
                self.decision,
            )
            == expected,
            "DECISION_DERIVATION_MISMATCH",
        )
        require(self.validation_order == VALIDATION_ORDER, "VALIDATION_ORDER_MISMATCH")
        require(not self.validation_failures, "VALID_RECORD_HAS_FAILURES")

    @property
    def record_digest(self) -> str:
        return canonical_digest(self)

    @property
    def operationally_eligible(self) -> bool:
        return False

    @property
    def real_evidence_write_allowed(self) -> bool:
        return False

    @property
    def external_claims_authenticated(self) -> bool:
        return False

    @property
    def activation_allowed(self) -> bool:
        return False

    @property
    def prospective_evidence(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class SyntheticPipelineResult:
    """A fail-closed result envelope; rejected inputs never yield a decision."""

    decision_record: SyntheticDecisionRecord | None
    state: DecisionState
    validation_failures: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.state is DecisionState.REJECTED:
            require(self.decision_record is None, "REJECTED_RESULT_HAS_DECISION")
            require(bool(self.validation_failures), "REJECTED_RESULT_NEEDS_FAILURE")
        else:
            require(self.decision_record is not None, "ACCEPTED_RESULT_NEEDS_DECISION")
            require(self.decision_record.decision is self.state, "RESULT_STATE_MISMATCH")
            require(not self.validation_failures, "ACCEPTED_RESULT_HAS_FAILURES")

    @property
    def real_evidence_write_allowed(self) -> bool:
        return False

    @property
    def external_claims_authenticated(self) -> bool:
        return False

    @property
    def activation_allowed(self) -> bool:
        return False

    @property
    def prospective_evidence(self) -> bool:
        return False


def run_synthetic_pipeline(
    transaction: SyntheticOperationalTransaction,
) -> SyntheticPipelineResult:
    """Evaluate locally and convert every contract failure into REJECTED."""
    if type(transaction) is not SyntheticOperationalTransaction:
        return SyntheticPipelineResult(
            None, DecisionState.REJECTED, ("WRONG_TRANSACTION_TYPE",)
        )
    try:
        record = build_synthetic_decision_record(transaction)
    except (ContractError, CoreThreeError, IntegrationError) as exc:
        return SyntheticPipelineResult(None, DecisionState.REJECTED, (str(exc),))
    except (ArithmeticError, AttributeError, RecursionError, TypeError, ValueError):
        return SyntheticPipelineResult(
            None, DecisionState.REJECTED, ("INVALID_INTEGRATION_INPUT",)
        )
    return SyntheticPipelineResult(record, record.decision, ())


def build_synthetic_decision_record(
    transaction: SyntheticOperationalTransaction,
) -> SyntheticDecisionRecord:
    """Build a reproducible mathematical decision that can never authorize a write."""
    transaction.validate()
    values = _decision_values(transaction)
    binding = transaction.binding
    replay = canonical_digest(
        (
            transaction.attempts.current.attempt_id,
            transaction.observation.response_id,
            transaction.activation.schedule.version,
            binding,
        )
    )
    return SyntheticDecisionRecord(
        transaction,
        binding,
        replay,
        *values[:-1],
        values[-1],
        VALIDATION_ORDER,
        (),
    )


def classify_edge(edge: float) -> DecisionState:
    """Apply the frozen strict-positive eligibility rule exactly."""
    require(type(edge) is float and math.isfinite(edge), "INVALID_EDGE")
    return DecisionState.POSITIVE_EDGE_CANDIDATE if edge > 0.0 else DecisionState.NO_BET


def _decision_values(
    transaction: SyntheticOperationalTransaction,
) -> tuple[float, float, float, float, str, int, float, float, DecisionState]:
    transaction.validate()
    preview = build_consensus_preview(transaction.observation)
    consensus = preview["market_consensus_home_probability"]
    require(type(consensus) is float and 0.0 < consensus < 1.0, "INVALID_CONSENSUS")
    def_epa = transaction.def_epa.validated_value(transaction.week)
    candidate = transaction.candidate
    raw = 1.0 / (
        1.0
        + math.exp(
            -(
                candidate.intercept
                + candidate.market_coefficient * consensus
                + candidate.def_epa_coefficient * def_epa
            )
        )
    )
    candidate_home = min(
        consensus + candidate.residual_cap,
        max(consensus - candidate.residual_cap, raw),
    )
    require(0.0 < candidate_home < 1.0, "INVALID_CANDIDATE_PROBABILITY")
    selected = "HOME" if candidate_home >= consensus else "AWAY"
    side_probability = candidate_home if selected == "HOME" else 1.0 - candidate_home
    execution = preview["execution"]
    offered = execution["home_odds" if selected == "HOME" else "away_odds"]
    try:
        break_even = american_odds_to_implied_probability(offered)
    except (TypeError, ValueError) as exc:
        raise IntegrationError("MALFORMED_OFFERED_PRICE") from exc
    require(0.0 < break_even < 1.0, "INVALID_BREAK_EVEN_PROBABILITY")
    edge = side_probability - break_even
    decision = classify_edge(edge)
    return (
        consensus,
        def_epa,
        candidate_home,
        candidate_home - consensus,
        selected,
        offered,
        break_even,
        edge,
        decision,
    )


__all__ = [
    "VALIDATION_ORDER",
    "AttemptHistory",
    "AttemptKind",
    "AttemptRecord",
    "AttemptState",
    "AuthorityDependency",
    "AuthorityKind",
    "AuthorityState",
    "DecisionState",
    "DefEpaInput",
    "DefEpaState",
    "FrozenCandidateContract",
    "IntegrationError",
    "SyntheticDecisionRecord",
    "SyntheticOperationalTransaction",
    "SyntheticPipelineResult",
    "build_synthetic_decision_record",
    "canonical_digest",
    "classify_edge",
    "expected_authority_artifact",
    "run_synthetic_pipeline",
    "synthetic_authority_dependencies",
    "transaction_authority_context_binding",
]
