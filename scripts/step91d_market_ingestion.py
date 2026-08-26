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
    commands.add_parser("capture")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one ingestion command with concise expected-error reporting."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "preview" and args.ledger is not None:
        parser.error("--ledger is forbidden for preview")
    if args.command == "capture" and args.ledger is None:
        parser.error("--ledger is required for capture")
    try:
        snapshot = load_market_snapshot(args.input)
        if args.command == "preview":
            event = preview_market_decision(snapshot)
        else:
            event = capture_market_decision(args.ledger, snapshot)
    except ProspectiveMarketIngestionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
