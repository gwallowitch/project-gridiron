"""Command-line interface for the Step 91C prospective ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gridiron.market.prospective_ledger import (
    capture_decision,
    ledger_summary,
    settle_decision,
    validate_ledger,
)


def _json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("input JSON must be an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with the ledger option before subcommands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    capture = commands.add_parser("capture")
    capture.add_argument("--input", required=True, type=Path)
    commands.add_parser("validate")

    settle = commands.add_parser("settle")
    settle.add_argument("--game-id", required=True)
    settle.add_argument(
        "--result", required=True, choices=("HOME", "AWAY", "PUSH", "CANCELLED")
    )
    settle.add_argument("--settled-at", required=True)
    commands.add_parser("summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute one ledger command and print canonical JSON."""
    args = build_parser().parse_args(argv)
    if args.command == "capture":
        result = capture_decision(args.ledger, _json_file(args.input))
    elif args.command == "validate":
        state = validate_ledger(args.ledger)
        result = {
            "valid": True,
            "decisions": len(state.decisions),
            "settlements": len(state.settlements),
        }
    elif args.command == "settle":
        result = settle_decision(
            args.ledger,
            game_id=args.game_id,
            result=args.result,
            settled_at=args.settled_at,
        )
    else:
        result = ledger_summary(args.ledger)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
