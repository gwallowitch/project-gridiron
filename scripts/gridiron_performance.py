"""Read-only Step 91W operational execution-performance reporter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.performance import (
    PerformanceAccountingError,
    build_performance_report,
)
from scripts.gridiron_settlement import (
    EXECUTIONS_PATH,
    SETTLEMENTS_PATH,
)


def _timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PerformanceAccountingError("through must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PerformanceAccountingError("through must include a timezone")
    return parsed.astimezone(UTC)


def _print_summary(report: dict[str, object]) -> None:
    cash = report["cash"]
    bonus = report["bonus_bet"]
    combined = report["combined"]
    clv = report["clv"]
    print("GRIDIRON OPERATIONAL PERFORMANCE")
    print("READ-ONLY | NON-PROSPECTIVE | DESCRIPTIVE ONLY")
    print(f"Executions: {report['execution_count']} ({report['unsettled_execution_count']} awaiting result)")
    print(f"CASH: staked {cash['total_cash_staked']:.2f}, net {cash['net_cash_profit']:.2f}, ROI {cash['cash_roi']}")
    print(f"BONUS_BET: face {bonus['settled_bonus_face_value']:.2f}, proceeds {bonus['bonus_cash_proceeds']:.2f}, conversion {bonus['conversion_rate']}")
    print(f"TOTAL REALIZED CASH CHANGE: {combined['total_realized_cash_change']:.2f}")
    print(f"CLV: {clv['available_count']} available, {clv['unavailable_count']} unavailable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("summary", "executions", "clv"))
    parser.add_argument("--executions", type=Path, default=EXECUTIONS_PATH)
    parser.add_argument("--settlements", type=Path, default=SETTLEMENTS_PATH)
    parser.add_argument("--game")
    parser.add_argument("--week", type=int)
    parser.add_argument("--funding-type", choices=("CASH", "BONUS_BET"))
    parser.add_argument("--through")
    parser.add_argument("--starting-cash", type=float)
    parser.add_argument("--starting-bonus", type=float)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        report = build_performance_report(
            args.executions,
            args.settlements,
            through=None if args.through is None else _timestamp(args.through),
            game_id=args.game,
            week=args.week,
            funding_type=args.funding_type,
            starting_cash=args.starting_cash,
            starting_bonus=args.starting_bonus,
        )
    except PerformanceAccountingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output: object = report
    if args.command == "executions":
        output = report["executions"]
    elif args.command == "clv":
        output = report["clv"]
    if args.json_output or args.command != "summary":
        print(json.dumps(output, sort_keys=True, separators=(",", ":"), allow_nan=False))
    else:
        _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
