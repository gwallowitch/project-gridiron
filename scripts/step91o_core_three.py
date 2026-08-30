"""Validate an offline Core-Three fixture as non-prospective test data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.core_three_operations import preview_non_evidence
from gridiron.market.core_three_types import CoreThreeError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", required=True, type=Path)
    parser.add_argument("--authoritative-event", required=True, type=Path)
    parser.add_argument("--receipt-at", required=True)
    parser.add_argument(
        "--test-timestamp-semantics-approved",
        action="store_true",
        help="synthetic-test switch only; never provider or governance evidence",
    )
    args = parser.parse_args(argv)
    try:
        response = json.loads(args.response.read_text(encoding="utf-8"))
        authoritative = json.loads(
            args.authoritative_event.read_text(encoding="utf-8")
        )
        result = preview_non_evidence(
            response,
            authoritative,
            receipt_at=args.receipt_at,
            timestamp_semantics_approved_for_test=(
                args.test_timestamp_semantics_approved
            ),
        )
    except (OSError, json.JSONDecodeError, CoreThreeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
