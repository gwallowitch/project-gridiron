"""Immutable contracts for the inactive Step 91O Core-Three protocol."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

PROTOCOL_ID = "step91o-2026-live-market-core-three-v1"
CANDIDATE_ID = "market-plus-def-epa-capped-0425-v1"
CANDIDATE_VARIANT_ID = "market-plus-def-epa-capped-0425-core-three-v1"
EVIDENCE_ID = "step91o-core-three-non-prospective-preview-v1"


def validate_identity(value: dict[str, Any]) -> None:
    for key, expected in {
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "candidate_variant_id": CANDIDATE_VARIANT_ID,
        "evidence_id": EVIDENCE_ID,
        "prospective_evidence": False,
    }.items():
        if key in value and (
            value[key] != expected or (expected is False and value[key] is not False)
        ):
            raise CoreThreeError("CORE_THREE_IDENTITY_MISMATCH")


def validate_safe_strings(value: Any) -> None:
    """Reject suspicious provenance without echoing it into errors."""
    if isinstance(value, str):
        if re.search(
            r"api[ _-]?key|token|secret|authorization|bearer|[?&].*=",
            value,
            re.IGNORECASE,
        ):
            raise CoreThreeError("UNSAFE_PROVENANCE_STRING")
    elif isinstance(value, dict):
        validate_identity(value)
        for key, item in value.items():
            validate_safe_strings(key)
            validate_safe_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_safe_strings(item)


class Jurisdiction(StrEnum):
    US_AGGREGATE = "US_AGGREGATE"
    US_STATE_SPECIFIC = "US_STATE_SPECIFIC"
    NON_US = "NON_US"
    GLOBAL_UNQUALIFIED = "GLOBAL_UNQUALIFIED"
    UNKNOWN = "UNKNOWN"


def validate_jurisdiction(value: object) -> None:
    # State-specific equivalence has not been approved. Aggregate is preview-only.
    if not isinstance(value, str) or value not in tuple(Jurisdiction):
        raise CoreThreeError("JURISDICTION_MALFORMED")
    if value != Jurisdiction.US_AGGREGATE:
        raise CoreThreeError("JURISDICTION_UNAPPROVED")


BOOK_KEYS = ("betmgm", "fanduel", "draftkings")
CANONICAL_BOOKS = {
    "betmgm": "BetMGM",
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
}
MARKET_KEYS = ("h2h", "spreads", "totals")
EXECUTION_BOOK_KEY = "draftkings"


class CoreThreeError(ValueError):
    """Raised when Core-Three input violates a deterministic contract."""


@dataclass(frozen=True, slots=True)
class Outcome:
    name: str
    price: int
    point: float | None
    sid: str | None


@dataclass(frozen=True, slots=True)
class Market:
    key: str
    last_update_text: str
    last_update: datetime
    outcomes: tuple[Outcome, Outcome]


@dataclass(frozen=True, slots=True)
class Book:
    key: str
    canonical_name: str
    sid: str | None
    markets: tuple[Market, Market, Market]

    def market(self, key: str) -> Market:
        return next(item for item in self.markets if item.key == key)


@dataclass(frozen=True, slots=True)
class AtomicObservation:
    protocol_id: str
    provider: str
    provider_event_id: str
    authoritative_game_id: str
    home_team: str
    away_team: str
    kickoff_at: datetime
    receipt_at: datetime
    jurisdiction: str
    books: tuple[Book, Book, Book]
    response_id: str
    response_digest: str
    receipt_at_text: str
    raw_payload_retained: bool = False
    prospective_evidence: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        validate_safe_strings(asdict(self))
        validate_identity(
            {
                "protocol_id": self.protocol_id,
                "prospective_evidence": self.prospective_evidence,
            }
        )
        validate_jurisdiction(self.jurisdiction)
        if self.raw_payload_retained is not False:
            raise CoreThreeError("RAW_RETENTION_PROHIBITED")
        if (
            not isinstance(self.response_id, str)
            or not self.response_id
            or not isinstance(self.response_digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", self.response_digest)
        ):
            raise CoreThreeError("RESPONSE_IDENTITY_REQUIRED")
        if self.provider != "The Odds API":
            raise CoreThreeError("PROVIDER_IDENTITY_MISMATCH")
        if _parse_aware_text(self.receipt_at_text) != self.receipt_at:
            raise CoreThreeError("RESPONSE_RECEIPT_MISMATCH")
        if (
            not isinstance(self.books, tuple)
            or tuple(book.key for book in self.books) != BOOK_KEYS
        ):
            raise CoreThreeError("EXACT_THREE_BOOK_ORDER_REQUIRED")
        for book in self.books:
            if book.canonical_name != CANONICAL_BOOKS[book.key]:
                raise CoreThreeError("CANONICAL_BOOK_IDENTITY_MISMATCH")
            if (
                not isinstance(book.markets, tuple)
                or tuple(m.key for m in book.markets) != MARKET_KEYS
            ):
                raise CoreThreeError("EXACT_THREE_MARKETS_REQUIRED")
            for market in book.markets:
                if _parse_aware_text(market.last_update_text) != market.last_update:
                    raise CoreThreeError("PROVIDER_TIMESTAMP_REPRESENTATION_MISMATCH")

    def book(self, key: str) -> Book:
        return next(item for item in self.books if item.key == key)

    def as_normalized_dict(self) -> dict[str, Any]:
        """Return a sanitized normalized record without raw provider bytes."""
        self.validate()
        return {
            "protocol_id": self.protocol_id,
            "candidate_variant_id": CANDIDATE_VARIANT_ID,
            "evidence_id": EVIDENCE_ID,
            "acquisition": {
                "response_id": self.response_id,
                "response_digest": self.response_digest,
                "provider_origin_authenticated": False,
                "receipt_at_text": self.receipt_at_text,
                "receipt_at": _utc_text(self.receipt_at),
                "boundary": "single_supplied_response_not_authenticated",
            },
            "classification": "NON_PROSPECTIVE_NORMALIZED_PREVIEW",
            "provider": self.provider,
            "provider_event_id": self.provider_event_id,
            "authoritative_game_id": self.authoritative_game_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "kickoff_at": _utc_text(self.kickoff_at),
            "receipt_at": _utc_text(self.receipt_at),
            "jurisdiction": self.jurisdiction,
            "books": [
                {
                    "key": book.key,
                    "canonical_name": book.canonical_name,
                    "sid": book.sid,
                    "markets": [
                        {
                            "key": market.key,
                            "last_update": _utc_text(market.last_update),
                            "last_update_text": market.last_update_text,
                            "outcomes": [
                                {
                                    "name": outcome.name,
                                    "price": outcome.price,
                                    "point": outcome.point,
                                    "sid": outcome.sid,
                                }
                                for outcome in market.outcomes
                            ],
                        }
                        for market in book.markets
                    ],
                }
                for book in self.books
            ],
            "raw_payload_retained": False,
            "prospective_evidence": False,
        }


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_aware_text(value: object) -> datetime:
    if not isinstance(value, str):
        raise CoreThreeError("INVALID_TIMESTAMP_REPRESENTATION")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CoreThreeError("INVALID_TIMESTAMP_REPRESENTATION") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CoreThreeError("TIMEZONE_REQUIRED")
    return parsed.astimezone(UTC)
