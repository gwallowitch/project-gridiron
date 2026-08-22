"""Validate Step 79F six-weight promotion from the research registry."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

REGISTRY = Path("data/reports/research/research_registry.json")
ROBUSTNESS = Path("data/reports/research/step79e_robustness.json")
OUTPUT = Path("data/reports/research/step79f_promotion.json")

SEASONS = (2022, 2023, 2024, 2025)
BASELINE = "six_weight_v1_baseline"
LOCKED = "six_weight_v1_locked"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _pick(row: dict, *keys: str):
    for key in keys:
        if key in row:
            return row[key]
    return None


def _extract(payload, name: str) -> dict[int, dict[str, float]]:
    found: dict[int, dict[str, float]] = {}

    for row in _walk(payload):
        row_name = _pick(row, "name", "experiment", "experiment_name")
        if row_name != name:
            continue

        season = _pick(row, "season")
        score = _pick(row, "selection_score", "score")
        accuracy = _pick(row, "winner_accuracy", "accuracy")

        try:
            season_i = int(season)
            score_f = float(score)
            accuracy_f = float(accuracy)
        except (TypeError, ValueError):
            continue

        if season_i in SEASONS:
            found[season_i] = {
                "selection_score": score_f,
                "winner_accuracy": accuracy_f,
            }

    return found


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"Missing research registry: {REGISTRY}")

    if not ROBUSTNESS.exists():
        raise FileNotFoundError(
            "Missing Step 79E robustness report. Run 79E before promotion."
        )

    robust = json.loads(ROBUSTNESS.read_text(encoding="utf-8"))

    if robust.get("status") != "PROVISIONAL_PASS":
        raise ValueError(
            "Step 79E did not produce PROVISIONAL_PASS; promotion is blocked."
        )

    if robust.get("candidate") != "def_sos_225":
        raise ValueError(
            "Step 79E provisional candidate is not def_sos_225."
        )

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    baseline = _extract(payload, BASELINE)
    locked = _extract(payload, LOCKED)

    missing = [
        f"{name}:{season}"
        for name, rows in ((BASELINE, baseline), (LOCKED, locked))
        for season in SEASONS
        if season not in rows
    ]
    if missing:
        raise ValueError(
            "Step 79F registry is missing required results: "
            + ", ".join(missing)
        )

    score_deltas = [
        locked[season]["selection_score"]
        - baseline[season]["selection_score"]
        for season in SEASONS
    ]
    accuracy_deltas = [
        locked[season]["winner_accuracy"]
        - baseline[season]["winner_accuracy"]
        for season in SEASONS
    ]

    leave_one_out: dict[str, float] = {}

    for excluded in SEASONS:
        kept = [
            delta
            for season, delta in zip(SEASONS, score_deltas, strict=True)
            if season != excluded
        ]
        leave_one_out[str(excluded)] = mean(kept)

    summary = {
        "step": "79F",
        "candidate": LOCKED,
        "defensive_schedule_difficulty_weight": 2.25,
        "mean_score_delta": mean(score_deltas),
        "mean_accuracy_delta": mean(accuracy_deltas),
        "season_wins": sum(delta < 0 for delta in score_deltas),
        "season_losses": sum(delta > 0 for delta in score_deltas),
        "season_ties": sum(delta == 0 for delta in score_deltas),
        "leave_one_season_out_mean_deltas": leave_one_out,
        "looso_improves_count": sum(
            delta < 0 for delta in leave_one_out.values()
        ),
        "worst_looso_delta": max(leave_one_out.values()),
    }

    passed = (
        summary["mean_score_delta"] < 0
        and summary["mean_accuracy_delta"] >= -0.002
        and summary["looso_improves_count"] == 4
        and summary["worst_looso_delta"] <= 0.0
    )
    summary["status"] = "PROMOTE" if passed else "HOLD"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 79F SIX-WEIGHT PROMOTION LOCK")
    print("=" * 96)
    print(f"Candidate......................... {LOCKED}")
    print("defensive_schedule_difficulty.... 2.25")
    print(f"Mean score delta.................. {summary['mean_score_delta']:+.6f}")
    print(f"Mean accuracy delta............... {summary['mean_accuracy_delta']:+.3%}")
    print(
        "Season record..................... "
        f"{summary['season_wins']}-"
        f"{summary['season_losses']}-"
        f"{summary['season_ties']}"
    )
    print(
        "LOOSO improvements................ "
        f"{summary['looso_improves_count']}/4"
    )
    print(
        "Worst LOOSO delta................. "
        f"{summary['worst_looso_delta']:+.6f}"
    )
    print(f"Status............................ {summary['status']}")
    print("=" * 96)
    print(f"Report: {OUTPUT.resolve()}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
