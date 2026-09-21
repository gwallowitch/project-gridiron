"""Materialize the pinned Step 92F outcome-free schedule and manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from gridiron.market.historical_spread_schedule import (
    HistoricalScheduleError,
    materialize_schedule_and_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--retrieved-at", required=True)
    args = parser.parse_args(argv)
    try:
        retrieved = datetime.fromisoformat(args.retrieved_at)
        if retrieved.tzinfo is None:
            raise HistoricalScheduleError("retrieved-at must include a timezone")
        result = materialize_schedule_and_manifest(
            args.source, args.output_root, retrieved_at=retrieved
        )
    except (OSError, ValueError, HistoricalScheduleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
