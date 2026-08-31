from __future__ import annotations

from copy import deepcopy

import pytest
from test_core_three_provider import normalize, response

from gridiron.market.core_three_consensus import build_consensus_preview
from gridiron.market.core_three_types import BOOK_KEYS, CoreThreeError
from gridiron.market.moneyline import remove_two_sided_vig


def test_equal_one_third_no_vig_consensus_and_draftkings_separation() -> None:
    payload = response()
    prices = {
        "betmgm": (155, -190),
        "fanduel": (164, -196),
        "draftkings": (150, -180),
    }
    for book in payload["bookmakers"]:
        away, home = prices[book["key"]]
        book["markets"][0]["outcomes"][0]["price"] = away
        book["markets"][0]["outcomes"][1]["price"] = home
    preview = build_consensus_preview(normalize(payload))
    expected = (
        sum(
            remove_two_sided_vig(home, away).home_fair_probability
            for away, home in prices.values()
        )
        / 3
    )
    assert preview["market_consensus_home_probability"] == pytest.approx(expected)
    assert preview["weight_per_book"] == pytest.approx(1 / 3)
    assert set(preview["book_home_probabilities"]) == set(BOOK_KEYS)
    assert preview["execution"] == {
        "book_key": "draftkings",
        "home_odds": -180,
        "away_odds": 150,
        "same_atomic_object": True,
        "state_equivalence": "UNRESOLVED",
    }
    assert preview["prospective_evidence"] is False


def test_input_order_does_not_change_consensus() -> None:
    payload = response()
    reversed_payload = deepcopy(payload)
    reversed_payload["bookmakers"].reverse()
    first = build_consensus_preview(normalize(payload))
    second = build_consensus_preview(normalize(reversed_payload))
    # Response fingerprints preserve supplied ordering; the consensus does not.
    first.pop("response_id")
    second.pop("response_id")
    assert first == second


def test_missing_book_cannot_reach_consensus() -> None:
    observation = normalize()
    object.__setattr__(observation, "books", observation.books[:2])
    with pytest.raises(CoreThreeError, match="EXACT_THREE_BOOK_ORDER_REQUIRED"):
        build_consensus_preview(observation)


def test_coefficients_remain_exact_and_no_seven_book_denominator() -> None:
    preview = build_consensus_preview(normalize())
    assert preview["candidate_coefficients"] == {
        "market": 4.980172,
        "def_epa": 1.044827,
        "intercept": -2.514766,
        "residual_cap": 0.0425,
    }
    assert preview["weight_per_book"] != pytest.approx(1 / 7)
