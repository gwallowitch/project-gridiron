"""Historical NFL moneyline threshold-research contracts and settlement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NFLMoneylineBetResult:
    """Flat-stake historical settlement for one eligible moneyline side."""

    season: int
    game_id: str
    team_id: str
    american_odds: int
    won: bool
    profit_units: float
    edge: float
    expected_roi: float


@dataclass(frozen=True, slots=True)
class NFLMoneylineThresholdSummary:
    """Aggregated historical performance for one threshold combination."""

    minimum_edge: float
    minimum_expected_roi: float
    bets: int
    wins: int
    losses: int
    win_rate: float
    profit_units: float
    roi: float
    average_edge: float
    average_expected_roi: float


def settle_flat_stake_moneyline(
    *,
    season: int,
    game_id: str,
    team_id: str,
    winning_team_id: str,
    american_odds: int,
    edge: float,
    expected_roi: float,
) -> NFLMoneylineBetResult:
    """Settle one historical moneyline side assuming one unit risked."""
    won = team_id == winning_team_id

    if won:
        if american_odds > 0:
            profit_units = american_odds / 100.0
        else:
            profit_units = 100.0 / abs(american_odds)
    else:
        profit_units = -1.0

    return NFLMoneylineBetResult(
        season=season,
        game_id=game_id,
        team_id=team_id,
        american_odds=american_odds,
        won=won,
        profit_units=profit_units,
        edge=edge,
        expected_roi=expected_roi,
    )


def summarize_threshold_results(
    results: tuple[NFLMoneylineBetResult, ...],
    *,
    minimum_edge: float,
    minimum_expected_roi: float,
) -> NFLMoneylineThresholdSummary:
    """Aggregate flat-stake historical results for one threshold pair."""
    bets = len(results)

    if bets == 0:
        return NFLMoneylineThresholdSummary(
            minimum_edge=minimum_edge,
            minimum_expected_roi=minimum_expected_roi,
            bets=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            profit_units=0.0,
            roi=0.0,
            average_edge=0.0,
            average_expected_roi=0.0,
        )

    wins = sum(result.won for result in results)
    losses = bets - wins
    profit_units = sum(result.profit_units for result in results)

    return NFLMoneylineThresholdSummary(
        minimum_edge=minimum_edge,
        minimum_expected_roi=minimum_expected_roi,
        bets=bets,
        wins=wins,
        losses=losses,
        win_rate=wins / bets,
        profit_units=profit_units,
        roi=profit_units / bets,
        average_edge=sum(result.edge for result in results) / bets,
        average_expected_roi=(
            sum(result.expected_roi for result in results) / bets
        ),
    )

from gridiron.market.eligibility import (
    NFLMoneylineEligibilityThresholds,
    evaluate_moneyline_eligibility,
)
from gridiron.market.evaluation import evaluate_moneyline_game
from gridiron.market.historical import NFLHistoricalMoneylineRecord
from gridiron.market.moneyline import NFLMoneylineSnapshot


def evaluate_historical_record(
    record: NFLHistoricalMoneylineRecord,
    *,
    thresholds: NFLMoneylineEligibilityThresholds,
) -> tuple[NFLMoneylineBetResult, ...]:
    """Evaluate and settle all eligible sides for one historical game."""
    snapshot = NFLMoneylineSnapshot(
        game_id=record.game_id,
        home_team_id=record.home_team_id,
        away_team_id=record.away_team_id,
        provider=record.provider,
        observed_timestamp=record.observed_timestamp,
        home_american_odds=record.home_american_odds,
        away_american_odds=record.away_american_odds,
    )

    evaluation = evaluate_moneyline_game(
        snapshot,
        home_calibrated_model_probability=(
            record.home_calibrated_model_probability
        ),
        away_calibrated_model_probability=(
            record.away_calibrated_model_probability
        ),
    )

    eligibility = evaluate_moneyline_eligibility(
        evaluation,
        thresholds=thresholds,
    )

    results: list[NFLMoneylineBetResult] = []

    if eligibility.home.eligible:
        results.append(
            settle_flat_stake_moneyline(
                season=record.season,
                game_id=record.game_id,
                team_id=record.home_team_id,
                winning_team_id=record.winning_team_id,
                american_odds=record.home_american_odds,
                edge=eligibility.home.edge,
                expected_roi=eligibility.home.expected_roi,
            )
        )

    if eligibility.away.eligible:
        results.append(
            settle_flat_stake_moneyline(
                season=record.season,
                game_id=record.game_id,
                team_id=record.away_team_id,
                winning_team_id=record.winning_team_id,
                american_odds=record.away_american_odds,
                edge=eligibility.away.edge,
                expected_roi=eligibility.away.expected_roi,
            )
        )

    return tuple(results)

from pathlib import Path

import polars as pl

from gridiron.calibration import calibrate_probability, load_temperature_contract


def load_historical_moneyline_records(
    *,
    prediction_paths: tuple[Path, ...],
    odds_path: Path,
    calibration_contract_path: Path,
    provider: str,
) -> tuple[NFLHistoricalMoneylineRecord, ...]:
    """Load and validate historical model/market records for threshold research."""
    contract = load_temperature_contract(calibration_contract_path)
    odds = pl.read_csv(odds_path)

    records: list[NFLHistoricalMoneylineRecord] = []

    for prediction_path in prediction_paths:
        predictions = pl.read_parquet(prediction_path)

        joined = predictions.join(
            odds,
            on="game_id",
            how="inner",
            suffix="_odds",
        )

        if joined.height != predictions.height:
            raise ValueError(
                f"Historical odds coverage mismatch for {prediction_path}: "
                f"{joined.height} matched of {predictions.height} predictions."
            )

        for row in joined.iter_rows(named=True):
            if row["home_team"] != row["home_team_odds"]:
                raise ValueError(
                    f"Home-team mismatch for {row['game_id']}: "
                    f"{row['home_team']} != {row['home_team_odds']}"
                )

            if row["away_team"] != row["away_team_odds"]:
                raise ValueError(
                    f"Away-team mismatch for {row['game_id']}: "
                    f"{row['away_team']} != {row['away_team_odds']}"
                )

            home_score = float(row["home_score"])
            away_score = float(row["away_score"])

            if home_score == away_score:
                continue

            winning_team_id = (
                row["home_team"]
                if home_score > away_score
                else row["away_team"]
            )

            raw_home_probability = float(row["home_win_probability"])
            calibrated_home_probability = calibrate_probability(
                raw_home_probability,
                slope=contract.slope,
            )
            calibrated_away_probability = 1.0 - calibrated_home_probability

            records.append(
                NFLHistoricalMoneylineRecord(
                    season=int(row["season"]),
                    week=int(row["week"]),
                    game_id=str(row["game_id"]),
                    home_team_id=str(row["home_team"]),
                    away_team_id=str(row["away_team"]),
                    provider=provider,
                    observed_timestamp=datetime.fromisoformat(
                        f"{row['gameday']}T12:00:00+00:00"
                    ),
                    home_american_odds=int(float(row["home_moneyline"])),
                    away_american_odds=int(float(row["away_moneyline"])),
                    home_calibrated_model_probability=(
                        calibrated_home_probability
                    ),
                    away_calibrated_model_probability=(
                        calibrated_away_probability
                    ),
                    winning_team_id=str(winning_team_id),
                )
            )

    return tuple(records)



def run_threshold_research(
    records: tuple[NFLHistoricalMoneylineRecord, ...],
    *,
    edge_thresholds: tuple[float, ...],
    expected_roi_thresholds: tuple[float, ...],
) -> tuple[NFLMoneylineThresholdSummary, ...]:
    """Evaluate every requested threshold pair across historical records."""
    summaries: list[NFLMoneylineThresholdSummary] = []

    for minimum_edge in edge_thresholds:
        for minimum_expected_roi in expected_roi_thresholds:
            thresholds = NFLMoneylineEligibilityThresholds(
                minimum_edge=minimum_edge,
                minimum_expected_roi=minimum_expected_roi,
            )

            results: list[NFLMoneylineBetResult] = []

            for record in records:
                results.extend(
                    evaluate_historical_record(
                        record,
                        thresholds=thresholds,
                    )
                )

            summaries.append(
                summarize_threshold_results(
                    tuple(results),
                    minimum_edge=minimum_edge,
                    minimum_expected_roi=minimum_expected_roi,
                )
            )

    return tuple(summaries)
