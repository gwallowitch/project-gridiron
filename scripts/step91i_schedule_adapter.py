"""Retain or validate the canonical NFLVerse schedule for Step 91I."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.prospective_schedule import (
    ProspectiveScheduleError,
    retain_schedule,
    validate_retained_file,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--retained", required=True, type=Path)
    parser.add_argument(
        "command", choices=("retain", "validate"), help="write once or validate only"
    )
    args = parser.parse_args(argv)
    try:
        result = (
            retain_schedule(args.source, args.retained)
            if args.command == "retain"
            else validate_retained_file(args.source, args.retained)
        )
    except (OSError, ProspectiveScheduleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
