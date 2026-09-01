"""Preview or capture an offline Step 91D market snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    capture_market_decision,
    load_market_snapshot,
    preview_market_decision,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with global paths before the subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--ledger", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preview")
    commands.add_parser("report")
    commands.add_parser("capture")
    return parser


def _percentage(value: object) -> str:
    """Format a returned probability or edge without changing its value."""
    return "N/A" if value is None else f"{float(value):.2%}"


def _american_odds(value: object) -> str:
    """Format a returned American price with an explicit positive sign."""
    return "N/A" if value is None else f"{int(value):+d}"


def format_market_report(event: dict[str, object]) -> str:
    """Present the exact preview event as a concise, non-prospective report."""
    model_home = event.get("candidate_home_probability")
    model_away = None if model_home is None else 1.0 - float(model_home)
    execution = event.get("execution_prices")
    prices = execution if isinstance(execution, dict) else {}
    is_bet = event.get("is_bet")
    selected_side = event.get("selected_side")
    decision = f"BET {selected_side}" if is_bet else "NO BET"
    lines = [
        "GRIDIRON WEEK 1 MARKET PREVIEW",
        "NON-PROSPECTIVE — PREVIEW ONLY",
        "",
        f"Game: {event.get('away_team', 'N/A')} @ {event.get('home_team', 'N/A')}",
        f"Kickoff: {event.get('kickoff_at', 'N/A')}",
        f"Candidate: {event.get('candidate_id', 'N/A')}",
        f"Model home probability: {_percentage(model_home)}",
        f"Model away probability: {_percentage(model_away)}",
        f"Market home probability: {_percentage(event.get('market_home_probability'))}",
        f"Selected edge: {_percentage(event.get('edge'))}",
        f"DraftKings home odds: {_american_odds(prices.get('home_odds'))}",
        f"DraftKings away odds: {_american_odds(prices.get('away_odds'))}",
        f"Selected side: {selected_side or 'N/A'}",
        f"Is bet: {is_bet}",
        f"Final decision: {decision}",
        "",
        "No prospective ledger written.",
        "No prospective evidence created.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run one ingestion command with concise expected-error reporting."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"preview", "report"} and args.ledger is not None:
        parser.error(f"--ledger is forbidden for {args.command}")
    if args.command == "capture" and args.ledger is None:
        parser.error("--ledger is required for capture")
    try:
        snapshot = load_market_snapshot(args.input)
        if args.command in {"preview", "report"}:
            event = preview_market_decision(snapshot)
        else:
            event = capture_market_decision(args.ledger, snapshot)
    except ProspectiveMarketIngestionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.command == "report":
        print(format_market_report(event))
    else:
        print(json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
