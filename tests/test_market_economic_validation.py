from __future__ import annotations

import numpy as np

from gridiron.market.economic_validation import (
    NFLFrozenEconomicGame,
    build_frozen_candidate_probabilities,
    summarize_frozen_economic_buckets,
)


def test_preferred_side_home_when_adjustment_positive() -> None:
    game = NFLFrozenEconomicGame(
        game_id="G1",
        market_home_probability=0.55,
        candidate_home_probability=0.57,
        home_american_odds=-120,
        away_american_odds=110,
        home_win=True,
    )

    observation = game.preferred_side()

    assert observation.side == "HOME"
    assert observation.won is True


def test_preferred_side_away_when_adjustment_negative() -> None:
    game = NFLFrozenEconomicGame(
        game_id="G1",
        market_home_probability=0.55,
        candidate_home_probability=0.53,
        home_american_odds=-120,
        away_american_odds=110,
        home_win=False,
    )

    observation = game.preferred_side()

    assert observation.side == "AWAY"
    assert observation.won is True


def test_candidate_probabilities_are_capped() -> None:
    train_market = np.array(
        [0.70, 0.30, 0.65, 0.35, 0.60, 0.40]
    )
    train_epa = np.array(
        [0.50, -0.50, 0.40, -0.40, 0.30, -0.30]
    )
    train_outcomes = np.array(
        [1, 0, 1, 0, 1, 0]
    )

    test_market = np.array(
        [0.55, 0.45]
    )
    test_epa = np.array(
        [1.0, -1.0]
    )

    result = build_frozen_candidate_probabilities(
        train_market_probabilities=train_market,
        train_def_epa=train_epa,
        train_outcomes=train_outcomes,
        test_market_probabilities=test_market,
        test_def_epa=test_epa,
    )

    assert len(result) == 2
    assert np.all(result >= 0.0)
    assert np.all(result <= 1.0)


def test_fixed_bucket_summary_returns_nonempty_groups() -> None:
    games = (
        NFLFrozenEconomicGame(
            game_id="G1",
            market_home_probability=0.50,
            candidate_home_probability=0.505,
            home_american_odds=-110,
            away_american_odds=-110,
            home_win=True,
        ),
        NFLFrozenEconomicGame(
            game_id="G2",
            market_home_probability=0.50,
            candidate_home_probability=0.515,
            home_american_odds=-110,
            away_american_odds=-110,
            home_win=False,
        ),
    )

    results = summarize_frozen_economic_buckets(games)

    assert tuple(result.label for result in results) == (
        "<1%",
        "1-2%",
    )
