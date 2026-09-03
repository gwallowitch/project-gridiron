from __future__ import annotations

import pytest

from gridiron.market.model_math import (
    CappedModelPosition,
    calculate_edge_decision,
    calculate_market_model_decision,
)
from gridiron.market.prospective_ledger import (
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
    build_decision,
)

BOOKS = ("Bet365", "SI", "Betway", "BetMGM", "FanDuel", "Caesars", "DraftKings")


def _payload(
    def_epa: float, *, draftkings_home: int = 120, draftkings_away: int = -140
) -> dict[str, object]:
    observations = []
    for book in BOOKS:
        home, away = (
            (draftkings_home, draftkings_away)
            if book == "DraftKings"
            else (110, -130)
        )
        observations.append(
            {
                "book": book,
                "home_odds": home,
                "away_odds": away,
                "observed_at": "2026-09-13T13:55:00Z",
            }
        )
    return {
        "game_id": "2026_01_BUF_NYJ",
        "season": 2026,
        "season_type": "REG",
        "week": 1,
        "kickoff_at": "2026-09-13T17:00:00Z",
        "decision_at": "2026-09-13T14:00:00Z",
        "home_team": "NYJ",
        "away_team": "BUF",
        "def_epa": def_epa,
        "market_observations": observations,
        "execution_prices": {
            "book": "DraftKings",
            "home_odds": draftkings_home,
            "away_odds": draftkings_away,
        },
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            _payload(0.2),
            (
                0.45449928168216974,
                0.4894225774829473,
                "HOME",
                120,
                0.45454545454545453,
                0.03487712293749279,
                True,
            ),
        ),
        (
            _payload(-0.2),
            (
                0.45449928168216974,
                0.41199928168216976,
                "AWAY",
                -140,
                0.5833333333333334,
                0.004667384984496814,
                True,
            ),
        ),
        (
            _payload(10.0),
            (
                0.45449928168216974,
                0.4969992816821697,
                "HOME",
                120,
                0.45454545454545453,
                0.042453827136715194,
                True,
            ),
        ),
        (
            _payload(-10.0),
            (
                0.45449928168216974,
                0.41199928168216976,
                "AWAY",
                -140,
                0.5833333333333334,
                0.004667384984496814,
                True,
            ),
        ),
        (
            _payload(10.0, draftkings_home=-200, draftkings_away=160),
            (
                0.4825264441227201,
                0.5250264441227201,
                "HOME",
                -200,
                0.6666666666666666,
                -0.14164022254394648,
                False,
            ),
        ),
    ],
)
def test_step91c_fixed_outputs_match_pre_extraction_baseline(
    payload: dict[str, object], expected: tuple[object, ...]
) -> None:
    event = build_decision(payload)
    actual = (
        event["market_home_probability"],
        event["candidate_home_probability"],
        event["selected_side"],
        event["selected_execution_odds"],
        event["break_even_probability"],
        event["edge"],
        event["is_bet"],
    )
    assert actual == expected


def test_shared_wrapper_reuses_exact_frozen_constants() -> None:
    decision = calculate_market_model_decision(
        0.45449928168216974,
        0.2,
        home_odds=120,
        away_odds=-140,
        market_coefficient=MARKET_COEFFICIENT,
        def_epa_coefficient=DEF_EPA_COEFFICIENT,
        intercept=INTERCEPT,
        residual_cap=RESIDUAL_CAP,
    )
    assert decision.model_home_probability == 0.4894225774829473
    assert decision.edge == 0.03487712293749279
    assert decision.is_bet is True


def test_strict_positive_edge_boundary_is_no_bet() -> None:
    position = CappedModelPosition(0.5, 0.5, "HOME", 0.5)
    decision = calculate_edge_decision(position, home_odds=100, away_odds=-100)
    assert decision.edge == 0.0
    assert decision.is_bet is False
