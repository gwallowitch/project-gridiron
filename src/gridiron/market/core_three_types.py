"""Immutable contracts for the inactive Step 91O Core-Three protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

PROTOCOL_ID = "step91o-2026-live-market-core-three-v1"
CANDIDATE_ID = "market-plus-def-epa-capped-0425-v1"
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
    raw_payload_retained: bool = False
    prospective_evidence: bool = False

    def book(self, key: str) -> Book:
        return next(item for item in self.books if item.key == key)

    def as_normalized_dict(self) -> dict[str, Any]:
        """Return a sanitized normalized record without raw provider bytes."""
        return {
            "protocol_id": self.protocol_id,
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
    return value.isoformat().replace("+00:00", "Z")
