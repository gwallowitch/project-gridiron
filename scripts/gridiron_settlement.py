"""Read-only Step 91T close and audit-ledger validation utility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.closing_settlement import (
    ClosingSettlementError,
    closing_line_from_history,
    read_executions,
    read_settlements,
)
from gridiron.market.operational_history import OperationalHistoryError

HISTORY_PATH = REPO_ROOT / "data" / "operational" / "market_history_v1.jsonl"
EXECUTIONS_PATH = REPO_ROOT / "data" / "operational" / "executions_v1.jsonl"
SETTLEMENTS_PATH = REPO_ROOT / "data" / "operational" / "settlements_v1.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    close = commands.add_parser("show-close")
    close.add_argument("--game", required=True)
    close.add_argument("--history", type=Path, default=HISTORY_PATH)
    executions = commands.add_parser("validate-executions")
    executions.add_argument("--executions", type=Path, default=EXECUTIONS_PATH)
    settlements = commands.add_parser("validate-settlements")
    settlements.add_argument("--settlements", type=Path, default=SETTLEMENTS_PATH)
    args = parser.parse_args(argv)
    try:
        if args.command == "show-close":
            result = closing_line_from_history(args.history, args.game)
        elif args.command == "validate-executions":
            result = {"valid": True, "execution_count": len(read_executions(args.executions))}
        else:
            result = {"valid": True, "settlement_count": len(read_settlements(args.settlements))}
    except (ClosingSettlementError, OperationalHistoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
