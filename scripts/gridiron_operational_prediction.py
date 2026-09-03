"""Run non-prospective decision support from three sportsbook prices."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from gridiron.market.model_math import calculate_market_model_decision
from gridiron.market.moneyline import remove_two_sided_vig
from gridiron.market.prospective_ledger import (
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
)

try:
    from scripts.step91d_three_book_exploratory import (
        BOOKS,
        ExploratoryPriceError,
        build_exploratory_price_view,
        load_exploratory_snapshot,
    )
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    from step91d_three_book_exploratory import (
        BOOKS,
        ExploratoryPriceError,
        build_exploratory_price_view,
        load_exploratory_snapshot,
    )

OPERATIONAL_IDENTITY = "market-plus-def-epa-capped-0425-operational-three-book-v1"


class OperationalPredictionError(ValueError):
    """Operational inputs cannot produce a safe non-prospective prediction."""


def build_operational_prediction(
    snapshot: dict[str, object], *, def_epa: float
) -> dict[str, object]:
    """Build deterministic live decision support without prospective side effects."""
    if isinstance(def_epa, bool) or not isinstance(def_epa, (int, float)):
        raise OperationalPredictionError("def_epa must be caller-supplied numeric input")
    def_epa = float(def_epa)
    if not math.isfinite(def_epa):
        raise OperationalPredictionError("def_epa must be finite")
    try:
        view = build_exploratory_price_view(snapshot)
    except ExploratoryPriceError as exc:
        raise OperationalPredictionError(str(exc)) from exc

    blocking_warnings = [
        warning
        for warning in view["warnings"]
        if (
            ":STALE_PRICE_" in warning
            or ":MISSING_PRICE" in warning
            or ":MISSING_TIMESTAMP" in warning
            or ":MISSING_BOOK" in warning
            or ":TIMESTAMP_AFTER_CAPTURE" in warning
        )
    ]
    if blocking_warnings:
        raise OperationalPredictionError(
            "fresh complete market data required: " + ", ".join(blocking_warnings)
        )

    if view["minutes_to_kickoff"] <= 0.0:
        raise OperationalPredictionError("prediction timestamp must be pre-kickoff")
    prices = view["prices"]
    fair_home: list[float] = []
    for book in BOOKS:
        offer = prices[book]
        home_odds = offer["home_odds"]
        away_odds = offer["away_odds"]
        if home_odds is None or away_odds is None:
            raise OperationalPredictionError(
                f"complete home and away prices required for {book}"
            )
        if offer["observed_at"] is None:
            raise OperationalPredictionError(f"observed_at required for {book}")
        fair_home.append(
            remove_two_sided_vig(home_odds, away_odds).home_fair_probability
        )
    market_home = sum(fair_home) / len(BOOKS)
    draftkings = prices["DraftKings"]
    decision = calculate_market_model_decision(
        market_home,
        def_epa,
        home_odds=draftkings["home_odds"],
        away_odds=draftkings["away_odds"],
        market_coefficient=MARKET_COEFFICIENT,
        def_epa_coefficient=DEF_EPA_COEFFICIENT,
        intercept=INTERCEPT,
        residual_cap=RESIDUAL_CAP,
    )
    return {
        **view,
        "operational_identity": OPERATIONAL_IDENTITY,
        "def_epa": def_epa,
        "market_home_probability": market_home,
        "market_away_probability": 1.0 - market_home,
        "model_home_probability": decision.model_home_probability,
        "model_away_probability": 1.0 - decision.model_home_probability,
        "selected_side": decision.selected_side,
        "selected_odds": decision.selected_odds,
        "edge": decision.edge,
        "is_bet": decision.is_bet,
        "coefficients": {
            "market": MARKET_COEFFICIENT,
            "def_epa": DEF_EPA_COEFFICIENT,
            "intercept": INTERCEPT,
            "residual_cap": RESIDUAL_CAP,
        },
    }


def _percentage(value: object) -> str:
    return f"{float(value):.2%}"


def format_operational_prediction(result: dict[str, object]) -> str:
    """Render a concise explicitly non-prospective prediction."""
    lines = [
        "GRIDIRON OPERATIONAL PREDICTION",
        "NON-PROSPECTIVE â€” LIVE DECISION SUPPORT",
        "",
        f"Game: {result['away_team']} @ {result['home_team']}",
        f"Game ID: {result['game_id']}",
        f"Kickoff: {result['kickoff_at']}",
        f"Prediction timestamp: {result['captured_at']}",
        f"Minutes to kickoff: {result['minutes_to_kickoff']:.1f}",
        f"Hours to kickoff: {result['minutes_to_kickoff'] / 60.0:.2f}",
        "",
        "Market books: BetMGM + FanDuel + DraftKings",
        "Market input: THREE-BOOK OPERATIONAL CONSENSUS",
    ]
    prices = result["prices"]
    for book in BOOKS:
        offer = prices[book]
        lines.append(
            f"  {book}: {offer['home_odds']:+d} / {offer['away_odds']:+d} "
            f"[{offer['observed_at']}]"
        )
    lines.extend(
        (
            "",
            f"Operational identity: {result['operational_identity']}",
            "Caller-supplied DEF EPA: " + str(result["def_epa"]),
            "Frozen coefficients reused: YES",
            "Residual cap reused: 4.25%",
            "Formal Step 91B prospective protocol: NO",
            "",
            "Operational market home probability: "
            + _percentage(result["market_home_probability"]),
            "Operational market away probability: "
            + _percentage(result["market_away_probability"]),
            "Model home probability: "
            + _percentage(result["model_home_probability"]),
            "Model away probability: "
            + _percentage(result["model_away_probability"]),
            f"Selected side: {result['selected_side']}",
            f"DraftKings selected odds: {result['selected_odds']:+d}",
            f"Edge: {_percentage(result['edge'])}",
            f"Decision: {'BET' if result['is_bet'] else 'NO BET'}",
            "",
            "Warnings:",
        )
    )
    lines.extend(f"  - {warning}" for warning in result["warnings"])
    if not result["warnings"]:
        lines.append("  None")
    lines.extend(
        (
            "",
            "THIS RESULT DOES NOT COUNT AS FORMAL PROSPECTIVE EVIDENCE.",
            "No prospective ledger written.",
            "No prospective evidence created.",
        )
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--def-epa", required=True, type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        snapshot = load_exploratory_snapshot(args.input)
        result = build_operational_prediction(snapshot, def_epa=args.def_epa)
    except (ExploratoryPriceError, OperationalPredictionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(format_operational_prediction(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
