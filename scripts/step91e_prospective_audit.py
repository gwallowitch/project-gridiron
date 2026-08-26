"""Run the deterministic Step 91E prospective pipeline audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gridiron.market.prospective_audit import (
    ProspectiveAuditError,
    audit_prospective_pipeline,
    canonical_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--snapshot", action="append", default=[], type=Path)
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_prospective_pipeline(args.repo_root, args.ledger, args.snapshot)
    except ProspectiveAuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
