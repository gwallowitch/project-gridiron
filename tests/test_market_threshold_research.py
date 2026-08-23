from __future__ import annotations

import pytest

from gridiron.market.threshold_research import (
    NFLMoneylineBetResult,
    settle_flat_stake_moneyline,
    summarize_threshold_results,
)


def test_positive_odds_win_settlement() -> None:
    result = settle_flat_stake_moneyline(
        season=2024,
        game_id="2024_01_A_B",
        team_id="A",
        winning_team_id="A",
        american_odds=150,
        edge=0.04,
        expected_roi=0.08,
    )

    assert result.won is True
    assert result.profit_units == pytest.approx(1.5)


def test_negative_odds_win_settlement() -> None:
    result = settle_flat_stake_moneyline(
        season=2024,
        game_id="2024_01_A_B",
        team_id="A",
        winning_team_id="A",
        american_odds=-150,
        edge=0.04,
        expected_roi=0.08,
    )

    assert result.won is True
    assert result.profit_units == pytest.approx(2 / 3)


def test_loss_settlement_is_minus_one_unit() -> None:
    result = settle_flat_stake_moneyline(
        season=2024,
        game_id="2024_01_A_B",
        team_id="A",
        winning_team_id="B",
        american_odds=200,
        edge=0.04,
        expected_roi=0.08,
    )

    assert result.won is False
    assert result.profit_units == pytest.approx(-1.0)


def test_summary_aggregates_results() -> None:
    results = (
        NFLMoneylineBetResult(
            season=2024,
            game_id="g1",
            team_id="A",
            american_odds=150,
            won=True,
            profit_units=1.5,
            edge=0.04,
            expected_roi=0.08,
        ),
        NFLMoneylineBetResult(
            season=2024,
            game_id="g2",
            team_id="B",
            american_odds=-120,
            won=False,
            profit_units=-1.0,
            edge=0.02,
            expected_roi=0.04,
        ),
    )

    summary = summarize_threshold_results(
        results,
        minimum_edge=0.01,
        minimum_expected_roi=0.02,
    )

    assert summary.bets == 2
    assert summary.wins == 1
    assert summary.losses == 1
    assert summary.win_rate == pytest.approx(0.5)
    assert summary.profit_units == pytest.approx(0.5)
    assert summary.roi == pytest.approx(0.25)
    assert summary.average_edge == pytest.approx(0.03)
    assert summary.average_expected_roi == pytest.approx(0.06)


def test_empty_summary_is_zeroed() -> None:
    summary = summarize_threshold_results(
        (),
        minimum_edge=0.05,
        minimum_expected_roi=0.10,
    )

    assert summary.bets == 0
    assert summary.wins == 0
    assert summary.losses == 0
    assert summary.win_rate == 0.0
    assert summary.profit_units == 0.0
    assert summary.roi == 0.0
    assert summary.average_edge == 0.0
    assert summary.average_expected_roi == 0.0

from datetime import UTC, datetime

from gridiron.market.eligibility import NFLMoneylineEligibilityThresholds
from gridiron.market.historical import NFLHistoricalMoneylineRecord
from gridiron.market.threshold_research import evaluate_historical_record


def _historical_record(
    *,
    home_probability: float = 0.60,
    away_probability: float = 0.40,
    winning_team_id: str = "HOME",
) -> NFLHistoricalMoneylineRecord:
    return NFLHistoricalMoneylineRecord(
        season=2024,
        week=1,
        game_id="2024_01_AWAY_HOME",
        home_team_id="HOME",
        away_team_id="AWAY",
        provider="historical-dataset",
        observed_timestamp=datetime(2024, 9, 1, 12, tzinfo=UTC),
        home_american_odds=120,
        away_american_odds=-140,
        home_calibrated_model_probability=home_probability,
        away_calibrated_model_probability=away_probability,
        winning_team_id=winning_team_id,
    )


def test_historical_record_can_produce_home_bet() -> None:
    results = evaluate_historical_record(
        _historical_record(),
        thresholds=NFLMoneylineEligibilityThresholds(),
    )

    assert len(results) == 1
    assert results[0].team_id == "HOME"
    assert results[0].won is True


def test_historical_record_can_produce_away_bet() -> None:
    results = evaluate_historical_record(
        _historical_record(
            home_probability=0.40,
            away_probability=0.60,
            winning_team_id="AWAY",
        ),
        thresholds=NFLMoneylineEligibilityThresholds(),
    )

    assert len(results) == 1
    assert results[0].team_id == "AWAY"
    assert results[0].won is True


def test_historical_record_can_produce_no_bets() -> None:
    results = evaluate_historical_record(
        _historical_record(),
        thresholds=NFLMoneylineEligibilityThresholds(
            minimum_edge=0.50,
            minimum_expected_roi=0.50,
        ),
    )

    assert results == ()
