"""Operate the frozen Step 91I real or dry-run prospective collection workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.prospective_operations import (
    ProspectiveOperationsError,
    capture_game,
    dry_run,
    game_day_checklist,
    initialize_manifest,
    operational_summary,
    record_game_status,
    settle_game,
)


def _common_live(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="The system collects evidence; it never learns from it during collection.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("initialize", help="register a retained schedule")
    initialize.add_argument("--schedule", required=True, type=Path)
    initialize.add_argument("--manifest", required=True, type=Path)
    capture = commands.add_parser("capture", help="capture one explicit real game")
    _common_live(capture)
    capture.add_argument("--raw", required=True, type=Path)
    capture.add_argument("--artifact-dir", required=True, type=Path)
    capture.add_argument("--game-id", required=True)
    capture.add_argument("--receipt-at", required=True)
    status = commands.add_parser(
        "status", help="record unavailable/postponed/cancelled"
    )
    status.add_argument("--manifest", required=True, type=Path)
    status.add_argument("--game-id", required=True)
    status.add_argument(
        "--state", required=True, choices=("unavailable", "postponed", "cancelled")
    )
    status.add_argument("--recorded-at", required=True)
    settle = commands.add_parser("settle", help="append one official result")
    _common_live(settle)
    settle.add_argument("--game-id", required=True)
    settle.add_argument(
        "--result", required=True, choices=("HOME", "AWAY", "PUSH", "CANCELLED")
    )
    settle.add_argument("--final-at", required=True)
    settle.add_argument("--settled-at", required=True)
    settle.add_argument("--result-source", required=True, type=Path)
    summary = commands.add_parser("summary", help="validate and summarize operations")
    _common_live(summary)
    summary.add_argument("--as-of", required=True)
    commands.add_parser("checklist", help="print objective game-day checks")
    rehearsal = commands.add_parser("dry-run", help="run isolated synthetic rehearsal")
    rehearsal.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "initialize":
            result = initialize_manifest(args.schedule, args.manifest)
        elif args.command == "capture":
            result = capture_game(
                args.manifest,
                args.ledger,
                args.raw,
                args.artifact_dir,
                game_id=args.game_id,
                receipt_at=args.receipt_at,
            )
        elif args.command == "status":
            result = record_game_status(
                args.manifest,
                game_id=args.game_id,
                status=args.state,
                recorded_at=args.recorded_at,
            )
        elif args.command == "settle":
            result = settle_game(
                args.manifest,
                args.ledger,
                game_id=args.game_id,
                result=args.result,
                final_at=args.final_at,
                settled_at=args.settled_at,
                result_source=args.result_source,
            )
        elif args.command == "summary":
            result = operational_summary(args.manifest, args.ledger, as_of=args.as_of)
        elif args.command == "checklist":
            result = game_day_checklist()
        else:
            result = dry_run(args.workspace)
    except (OSError, ProspectiveOperationsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
