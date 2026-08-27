"""Print the deterministic read-only Step 91G readiness audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gridiron.market.prospective_readiness import (
    ProspectiveReadinessError,
    canonical_json,
    readiness_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument(
        "--repo-root", default=Path(__file__).resolve().parents[1], type=Path
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = readiness_report(args.repo_root, args.ledger)
    except ProspectiveReadinessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
