"""Operate and summarize genuine Step 91F prospective evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gridiron.market.prospective_evidence import (
    ProspectiveEvidenceError,
    canonical_json,
    capture_real_snapshot,
    evidence_summary,
    protocol_completeness,
    settle_real_observation,
    validate_real_ledger,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument(
        "--repo-root", default=Path(__file__).resolve().parents[1], type=Path
    )
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--input", required=True, type=Path)
    settle = commands.add_parser("settle")
    settle.add_argument("--game-id", required=True)
    settle.add_argument(
        "--result", required=True, choices=("HOME", "AWAY", "PUSH", "CANCELLED")
    )
    settle.add_argument("--settled-at", required=True)
    commands.add_parser("validate")
    commands.add_parser("summary")
    commands.add_parser("protocol")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "capture":
            result = capture_real_snapshot(args.ledger, args.input)
        elif args.command == "settle":
            result = settle_real_observation(
                args.ledger,
                game_id=args.game_id,
                result=args.result,
                settled_at=args.settled_at,
            )
        elif args.command == "validate":
            result = validate_real_ledger(args.ledger)
        elif args.command == "summary":
            result = evidence_summary(args.repo_root, args.ledger)
        else:
            result = protocol_completeness(args.repo_root)
    except ProspectiveEvidenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
