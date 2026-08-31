"""Offline, in-memory adversarial regressions for the independent audit."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from test_core_three_lifecycle import GAME, scheduled
from test_core_three_provider import authoritative, normalize, response

from gridiron.market.core_three_consensus import build_consensus_preview
from gridiron.market.core_three_lifecycle import append_event, validate_chain
from gridiron.market.core_three_provider import (
    assert_external_gates,
    normalize_event_response,
)
from gridiron.market.core_three_types import (
    CANDIDATE_VARIANT_ID,
    EVIDENCE_ID,
    CoreThreeError,
)


def event(kind, **fields):
    return {"event_type": kind, "game_id": GAME, **fields}


def revision(**fields):
    return event(
        "SCHEDULE_REVISION",
        **{
            "old_kickoff_at": "2026-09-10T00:20:00Z",
            "new_kickoff_at": "2026-09-11T00:20:00Z",
            "detected_at": "2026-09-09T23:00:00Z",
            **fields,
        },
    )


def test_orphan_and_postponed_acceptance_rejected():
    with pytest.raises(CoreThreeError, match="PRECEDING_SCHEDULE"):
        append_event((), event("CAPTURE_ACCEPTED"))
    chain = append_event(scheduled(), event("GAME_POSTPONED"))
    with pytest.raises(CoreThreeError, match="POSTPONED"):
        append_event(chain, event("CAPTURE_ACCEPTED"))
    revised = append_event(chain, revision())
    validate_chain(append_event(revised, event("CAPTURE_ACCEPTED")))


@pytest.mark.parametrize("field", ["old_kickoff_at", "new_kickoff_at", "detected_at"])
@pytest.mark.parametrize("bad", [None, "", "invalid", "2026-09-09T23:00:00"])
def test_invalid_revision_timestamps(field, bad):
    with pytest.raises(CoreThreeError):
        append_event(scheduled(), revision(**{field: bad}))


def test_revision_old_schedule_and_detection_order():
    chain = append_event(scheduled(), revision())
    with pytest.raises(CoreThreeError, match="OLD_KICKOFF_MISMATCH"):
        append_event(chain, revision())
    with pytest.raises(CoreThreeError, match="OUT_OF_ORDER"):
        append_event(
            chain,
            revision(
                old_kickoff_at="2026-09-11T00:20:00Z",
                new_kickoff_at="2026-09-12T00:20:00Z",
                detected_at="2026-09-08T23:00:00Z",
            ),
        )


@pytest.mark.parametrize(
    "kind",
    [
        "CAPTURE_ACCEPTED",
        "SCHEDULED",
        "GAME_POSTPONED",
        "SCHEDULE_REVISION",
        "GAME_CANCELLED",
    ],
)
def test_cancelled_is_terminal(kind):
    chain = append_event(scheduled(), event("GAME_CANCELLED"))
    with pytest.raises(CoreThreeError, match="TERMINAL"):
        append_event(chain, event(kind))


def test_deep_copy_isolation_and_semantically_invalid_rehashed_chain():
    payload = event("SCHEDULED", metadata={"items": ["original"]})
    chain = append_event((), payload)
    payload["metadata"]["items"].append("changed")
    copied = append_event(chain, event("CAPTURE_REJECTED"))
    copied[0]["metadata"]["items"].append("changed")
    assert chain[0]["metadata"]["items"] == ["original"]
    validate_chain(chain)
    bad = deepcopy(list(chain))
    bad[0]["event_type"] = "CAPTURE_ACCEPTED"
    bad[0]["event_hash"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in bad[0].items() if k != "event_hash"},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    with pytest.raises(CoreThreeError, match="PRECEDING_SCHEDULE"):
        validate_chain(bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol_id", "step91i-seven-book"),
        ("evidence_id", "foreign"),
        ("candidate_variant_id", "seven-book"),
        ("prospective_evidence", True),
    ],
)
def test_foreign_identity_rejected_in_inputs_and_chains(field, value):
    with pytest.raises(CoreThreeError, match="IDENTITY"):
        append_event((), event("SCHEDULED", **{field: value}))
    payload = response()
    payload[field] = value
    with pytest.raises(CoreThreeError, match="IDENTITY"):
        normalize(payload)


def test_structural_identity_and_consensus_defense():
    observation = normalize()
    with pytest.raises(CoreThreeError, match="IDENTITY"):
        replace(observation, protocol_id="step91i-seven-book")
    object.__setattr__(observation, "protocol_id", "foreign")
    with pytest.raises(CoreThreeError, match="IDENTITY"):
        build_consensus_preview(observation)


@pytest.mark.parametrize(
    "jurisdiction",
    [
        "US_STATE_SPECIFIC",
        "NON_US",
        "GLOBAL_UNQUALIFIED",
        "UNKNOWN",
        "US_AGGREGATE_UNRESOLVED",
        None,
        [],
        1,
        "",
    ],
)
def test_unapproved_jurisdictions(jurisdiction):
    with pytest.raises(CoreThreeError, match="JURISDICTION"):
        normalize_event_response(
            response(),
            authoritative(),
            receipt_at="2026-09-09T23:20:00Z",
            timestamp_semantics_approved=True,
            jurisdiction=jurisdiction,
        )


@pytest.mark.parametrize("level", ["book", "market", "outcome"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("suspended", True),
        ("locked", True),
        ("active", False),
        ("active", "false"),
        ("suspended", None),
        ("locked", 0),
    ],
)
def test_unavailable_or_malformed_flags(level, field, value):
    payload = response()
    book = payload["bookmakers"][0]
    target = {
        "book": book,
        "market": book["markets"][0],
        "outcome": book["markets"][0]["outcomes"][0],
    }[level]
    target[field] = value
    with pytest.raises(CoreThreeError):
        normalize(payload)


@pytest.mark.parametrize(
    "text",
    [
        "apiKey=SYNTHETIC_SENTINEL",
        "API key SYNTHETIC_SENTINEL",
        "token=SYNTHETIC_SENTINEL",
        "secret=SYNTHETIC_SENTINEL",
        "authorization SYNTHETIC_SENTINEL",
        "Bearer SYNTHETIC_SENTINEL",
        "https://example.invalid/?credential=SYNTHETIC_SENTINEL",
    ],
)
def test_synthetic_credentials_never_echo(text):
    payload = response()
    payload["bookmakers"][0]["sid"] = text
    with pytest.raises(CoreThreeError) as caught:
        normalize(payload)
    assert "SYNTHETIC_SENTINEL" not in str(caught.value)


def test_exact_lines_and_wrong_sport():
    payload = response()
    payload["bookmakers"][0]["markets"][1]["outcomes"][0]["point"] = 3.500000002
    with pytest.raises(CoreThreeError, match="CONFLICTING_LINE"):
        normalize(payload)
    payload = response()
    payload["sport_key"] = "basketball_nba"
    with pytest.raises(CoreThreeError, match="SPORT"):
        normalize(payload)


def test_timestamp_serialization_and_response_fingerprint():
    payload = response()
    payload["bookmakers"][0]["markets"][0]["last_update"] = "2026-09-09T18:19:00-05:00"
    observation = normalize(payload)
    serialized = observation.as_normalized_dict()
    market = serialized["books"][0]["markets"][0]
    assert market["last_update_text"] == "2026-09-09T18:19:00-05:00"
    assert market["last_update"] == "2026-09-09T23:19:00Z"
    assert serialized["acquisition"]["provider_origin_authenticated"] is False
    assert serialized["acquisition"]["receipt_at_text"] == "2026-09-09T23:20:00Z"
    assert serialized["candidate_variant_id"] == CANDIDATE_VARIANT_ID
    assert serialized["evidence_id"] == EVIDENCE_ID
    payload["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = 160
    assert normalize(payload).response_digest != observation.response_digest


@pytest.mark.parametrize(
    "field,value",
    [("response_id", "another-call"), ("receipt_at", "2026-09-09T23:19:00Z")],
)
def test_conflicting_component_provenance(field, value):
    payload = response()
    payload["bookmakers"][0]["markets"][0][field] = value
    with pytest.raises(CoreThreeError, match="RESPONSE_"):
        normalize(payload)


def test_caller_flags_cannot_authorize_activation():
    with pytest.raises(CoreThreeError, match="NOT_AUTHENTICATED"):
        assert_external_gates(
            timestamp_semantics_approved=True,
            jurisdiction_approved=True,
            draftkings_execution_state_approved=True,
            retention_approved=True,
            authoritative_kickoff_approved=True,
            governance_approved=True,
            effective_timestamp="2000-01-01T00:00:00Z",
        )


def test_consistent_explicit_acquisition_and_available_flags():
    payload = response()
    payload["response_id"] = "synthetic-response-1"
    for book in payload["bookmakers"]:
        for component in (book, *book["markets"]):
            component.update(
                response_id="synthetic-response-1",
                active=True,
                suspended=False,
                locked=False,
                receipt_at="2026-09-09T18:20:00-05:00",
            )
    observation = normalize_event_response(
        payload,
        authoritative(),
        response_id="synthetic-response-1",
        receipt_at="2026-09-09T23:20:00Z",
        timestamp_semantics_approved=True,
        jurisdiction="US_AGGREGATE",
    )
    assert observation.response_id == "synthetic-response-1"
    assert sum(len(book.markets) for book in observation.books) == 9


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol_id", "foreign"),
        ("evidence_id", "foreign"),
        ("prospective_evidence", True),
    ],
)
def test_rehashed_foreign_chain_rejected(field, value):
    chain = deepcopy(list(scheduled()))
    chain[0][field] = value
    chain[0]["event_hash"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in chain[0].items() if k != "event_hash"},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    with pytest.raises(CoreThreeError, match="IDENTITY"):
        validate_chain(chain)


def test_direct_object_cannot_serialize_synthetic_credential():
    observation = normalize()
    bad_book = replace(observation.books[0], sid="Bearer SYNTHETIC_SENTINEL")
    with pytest.raises(CoreThreeError, match="UNSAFE_PROVENANCE"):
        replace(observation, books=(bad_book, *observation.books[1:]))


def test_direct_object_receipt_and_market_timestamp_consistency():
    observation = normalize()
    with pytest.raises(CoreThreeError, match="RESPONSE_RECEIPT_MISMATCH"):
        replace(observation, receipt_at_text="2026-09-09T23:19:00Z")
    market = replace(
        observation.books[0].markets[0], last_update_text="2026-09-09T23:18:00Z"
    )
    book = replace(
        observation.books[0], markets=(market, *observation.books[0].markets[1:])
    )
    with pytest.raises(CoreThreeError, match="TIMESTAMP_REPRESENTATION_MISMATCH"):
        replace(observation, books=(book, *observation.books[1:]))
