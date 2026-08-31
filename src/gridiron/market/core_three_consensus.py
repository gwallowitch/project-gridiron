"""Pure Core-Three consensus and candidate-input construction."""

from __future__ import annotations

from typing import Any

from gridiron.market.core_three_types import (
    BOOK_KEYS,
    CANDIDATE_ID,
    CANDIDATE_VARIANT_ID,
    EVIDENCE_ID,
    EXECUTION_BOOK_KEY,
    PROTOCOL_ID,
    AtomicObservation,
    CoreThreeError,
)
from gridiron.market.moneyline import remove_two_sided_vig

MARKET_COEFFICIENT = 4.980172
DEF_EPA_COEFFICIENT = 1.044827
INTERCEPT = -2.514766
RESIDUAL_CAP = 0.0425


def build_consensus_preview(observation: AtomicObservation) -> dict[str, Any]:
    """Build a non-evidence equal-weight preview from all three books."""
    observation.validate()
    if tuple(book.key for book in observation.books) != BOOK_KEYS:
        raise CoreThreeError("EXACT_THREE_BOOK_ORDER_REQUIRED")
    fair_by_book: dict[str, float] = {}
    prices_by_book: dict[str, dict[str, int]] = {}
    for book in observation.books:
        market = book.market("h2h")
        by_name = {outcome.name: outcome for outcome in market.outcomes}
        if set(by_name) != {observation.home_team, observation.away_team}:
            raise CoreThreeError(f"{book.key}: INCOMPLETE_MONEYLINE")
        home_odds = by_name[observation.home_team].price
        away_odds = by_name[observation.away_team].price
        fair = remove_two_sided_vig(home_odds, away_odds)
        fair_by_book[book.key] = fair.home_fair_probability
        prices_by_book[book.key] = {"home_odds": home_odds, "away_odds": away_odds}
    consensus = sum(fair_by_book.values()) / 3.0
    execution = prices_by_book[EXECUTION_BOOK_KEY]
    return {
        "classification": "NON_PROSPECTIVE_CONSENSUS_PREVIEW",
        "candidate_id": CANDIDATE_ID,
        "candidate_variant_id": CANDIDATE_VARIANT_ID,
        "evidence_id": EVIDENCE_ID,
        "protocol_id": PROTOCOL_ID,
        "response_id": observation.response_id,
        "market_consensus_home_probability": consensus,
        "book_home_probabilities": fair_by_book,
        "weight_per_book": 1.0 / 3.0,
        "execution": {
            "book_key": EXECUTION_BOOK_KEY,
            **execution,
            "same_atomic_object": True,
            "state_equivalence": "UNRESOLVED",
        },
        "candidate_coefficients": {
            "market": MARKET_COEFFICIENT,
            "def_epa": DEF_EPA_COEFFICIENT,
            "intercept": INTERCEPT,
            "residual_cap": RESIDUAL_CAP,
        },
        "prospective_evidence": False,
    }
