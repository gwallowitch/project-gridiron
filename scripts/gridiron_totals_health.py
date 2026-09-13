"""Read-only health check for Step 91R totals collection state."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    OperationalTotalsError,
    read_totals_history,
)
from gridiron.market.totals_collection_attempts import (
    TotalsAttemptError,
    read_totals_attempts,
)
from scripts.gridiron_totals_collector import ATTEMPT_PATH, HISTORY_PATH


def inspect_totals_health(
    history_path: Path | str = HISTORY_PATH,
    attempt_path: Path | str = ATTEMPT_PATH,
) -> dict[str, Any]:
    """Validate both immutable logs and their cross-file relationships."""
    history = read_totals_history(history_path)
    attempts = read_totals_attempts(attempt_path)
    automatic: dict[tuple[str, str], dict[str, Any]] = {}
    by_id = {row["observation_id"]: row for row in history}
    for row in history:
        provider = row["provider"]
        if provider.startswith(AUTOMATIC_PROVIDER_PREFIX):
            target = provider.removeprefix(AUTOMATIC_PROVIDER_PREFIX)
            key = (row["game"]["game_id"], target)
            if key in automatic:
                raise OperationalTotalsError("duplicate automatic totals observation")
            automatic[key] = row

    successful: set[tuple[str, str]] = set()
    counts = Counter(row["result"] for row in attempts)
    for attempt in attempts:
        if attempt["result"] != "SUCCESS":
            continue
        key = (attempt["game_id"], attempt["target_label"])
        observation = by_id.get(attempt["observation_id"])
        if (
            observation is None
            or automatic.get(key) != observation
            or attempt["attempted_at"] != observation["timing"]["collected_at"]
            or attempt["kickoff_at"] != observation["game"]["kickoff_at"]
        ):
            raise TotalsAttemptError("successful totals attempt linkage is invalid")
        successful.add(key)

    orphan_keys = sorted(set(automatic) - successful)
    latest = max(
        history,
        key=lambda row: row["timing"]["collected_at"],
        default=None,
    )
    return {
        "status": "RECOVERY_REQUIRED" if orphan_keys else "READY",
        "history_valid": True,
        "attempts_valid": True,
        "observation_count": len(history),
        "attempt_count": len(attempts),
        "success_count": counts["SUCCESS"],
        "failed_count": counts["FAILED"],
        "missed_window_count": counts["MISSED_WINDOW"],
        "post_kickoff_count": counts["POST_KICKOFF"],
        "latest_observation_time": None if latest is None else latest["timing"]["collected_at"],
        "latest_target_label": None if latest is None else latest["timing"]["target_label"],
        "recovery_required_count": len(orphan_keys),
        "recovery_required": [f"{game_id}:{target}" for game_id, target in orphan_keys],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-path", type=Path, default=HISTORY_PATH)
    parser.add_argument("--attempt-path", type=Path, default=ATTEMPT_PATH)
    args = parser.parse_args(argv)
    try:
        report = inspect_totals_health(args.history_path, args.attempt_path)
    except (OperationalTotalsError, TotalsAttemptError, OSError) as exc:
        print(f"TOTALS HEALTH: CORRUPT — {exc}", file=sys.stderr)
        return 2
    print(f"TOTALS HEALTH: {report['status']}")
    for field in (
        "observation_count", "attempt_count", "success_count", "failed_count",
        "missed_window_count", "post_kickoff_count", "latest_observation_time",
        "latest_target_label", "recovery_required_count",
    ):
        print(f"{field}: {report[field]}")
    return 1 if report["recovery_required_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
