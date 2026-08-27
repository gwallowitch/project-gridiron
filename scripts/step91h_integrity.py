"""Validate or export the Step 91H offline integrity chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.prospective_integrity import (
    ProspectiveIntegrityError,
    audit_manifest,
    export_anchor,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--as-of", required=True)
    commands.add_parser("anchor")
    args = parser.parse_args(argv)
    try:
        result = (
            audit_manifest(args.manifest, args.ledger, as_of=args.as_of)
            if args.command == "audit"
            else export_anchor(args.manifest)
        )
    except ProspectiveIntegrityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
