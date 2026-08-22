"""Step 79E robustness analysis from the Project Gridiron research registry."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

REGISTRY = Path("data/reports/research/research_registry.json")
OUTPUT = Path("data/reports/research/step79e_robustness.json")
SEASONS = (2022, 2023, 2024, 2025)

BASELINE = "def_sos_v1_baseline"
CANDIDATES = (
    "def_sos_150",
    "def_sos_200",
    "def_sos_225",
    "def_sos_250",
    "def_sos_275",
)


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


def extract(payload, name: str) -> dict[int, dict[str, float]]:
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


def candidate_stats(
    baseline: dict[int, dict[str, float]],
    rows: dict[int, dict[str, float]],
) -> dict[str, object]:
    score_deltas = [
        rows[season]["selection_score"]
        - baseline[season]["selection_score"]
        for season in SEASONS
    ]
    accuracy_deltas = [
        rows[season]["winner_accuracy"]
        - baseline[season]["winner_accuracy"]
        for season in SEASONS
    ]

    leave_one_out = {}
    for excluded in SEASONS:
        kept = [
            delta
            for season, delta in zip(SEASONS, score_deltas, strict=True)
            if season != excluded
        ]
        leave_one_out[str(excluded)] = mean(kept)

    return {
        "mean_score_delta": mean(score_deltas),
        "mean_accuracy_delta": mean(accuracy_deltas),
        "wins": sum(delta < 0 for delta in score_deltas),
        "losses": sum(delta > 0 for delta in score_deltas),
        "ties": sum(delta == 0 for delta in score_deltas),
        "leave_one_season_out_mean_deltas": leave_one_out,
        "looso_improves_count": sum(
            delta < 0 for delta in leave_one_out.values()
        ),
        "worst_looso_delta": max(leave_one_out.values()),
    }


def choose_candidate(stats: dict[str, dict[str, object]]) -> tuple[str, str]:
    ranked = sorted(
        stats,
        key=lambda name: (
            stats[name]["mean_score_delta"],
            -stats[name]["mean_accuracy_delta"],
            float(name.rsplit("_", 1)[-1]),
        ),
    )

    best = ranked[0]
    best_stats = stats[best]

    if best_stats["mean_score_delta"] >= 0:
        return best, "PARK"

    if best_stats["looso_improves_count"] < 3:
        return best, "HOLD"

    if best_stats["worst_looso_delta"] > 0.0005:
        return best, "HOLD"

    if best_stats["mean_accuracy_delta"] < -0.002:
        return best, "HOLD"

    # Prefer a lower/central weight when effectively tied with the numerical winner.
    for preferred in ("def_sos_225", "def_sos_200", "def_sos_250"):
        if preferred not in stats:
            continue
        gap = (
            stats[preferred]["mean_score_delta"]
            - best_stats["mean_score_delta"]
        )
        if (
            gap <= 0.00010
            and stats[preferred]["looso_improves_count"] >= 3
            and stats[preferred]["mean_accuracy_delta"] >= -0.002
        ):
            best = preferred
            break

    return best, "PROVISIONAL_PASS"


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"Research registry not found: {REGISTRY}")

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    baseline = extract(payload, BASELINE)

    missing_baseline = [
        season for season in SEASONS if season not in baseline
    ]
    if missing_baseline:
        raise ValueError(
            "79E baseline is missing seasons: "
            + ", ".join(str(x) for x in missing_baseline)
        )

    stats: dict[str, dict[str, object]] = {}

    for candidate in CANDIDATES:
        rows = extract(payload, candidate)
        missing = [
            season for season in SEASONS if season not in rows
        ]
        if missing:
            raise ValueError(
                f"{candidate} is missing seasons: "
                + ", ".join(str(x) for x in missing)
            )
        stats[candidate] = candidate_stats(baseline, rows)

    winner, status = choose_candidate(stats)

    report = {
        "step": "79E",
        "candidate": winner,
        "status": status,
        "stats": stats,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 79E DEFENSIVE SOS ROBUSTNESS")
    print("=" * 96)

    for name, values in stats.items():
        print(
            f"{name:<14} "
            f"MeanDelta={values['mean_score_delta']:+.6f}  "
            f"AccDelta={values['mean_accuracy_delta']:+.3%}  "
            f"W-L-T={values['wins']}-{values['losses']}-{values['ties']}  "
            f"LOOSO wins={values['looso_improves_count']}/4  "
            f"WorstLOOSO={values['worst_looso_delta']:+.6f}"
        )

    print("-" * 96)
    print(f"Candidate................ {winner}")
    print(f"Status................... {status}")
    print("=" * 96)
    print(f"Report: {OUTPUT.resolve()}")

    return 0 if status != "PARK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
