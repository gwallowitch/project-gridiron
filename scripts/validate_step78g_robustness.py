"""Step 78G robustness analysis from the Project Gridiron research registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

REGISTRY = Path("data/reports/research/research_registry.json")
TARGETS = {
    "recent_form_v1_baseline",
    "def_epa_trend_050",
    "def_epa_trend_0525",
    "def_epa_trend_055",
}
SEASONS = (2022, 2023, 2024, 2025)


@dataclass(frozen=True, slots=True)
class Result:
    name: str
    season: int
    selection_score: float
    winner_accuracy: float


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _pick(row: dict, *names: str):
    for name in names:
        if name in row:
            return row[name]
    return None


def extract_results(payload) -> list[Result]:
    found: dict[tuple[str, int], Result] = {}

    for row in _walk(payload):
        name = _pick(row, "name", "experiment", "experiment_name")
        season = _pick(row, "season")
        score = _pick(row, "selection_score", "score")
        accuracy = _pick(row, "winner_accuracy", "accuracy")

        if name not in TARGETS:
            continue

        try:
            result = Result(
                name=str(name),
                season=int(season),
                selection_score=float(score),
                winner_accuracy=float(accuracy),
            )
        except (TypeError, ValueError):
            continue

        if result.season in SEASONS:
            found[(result.name, result.season)] = result

    return list(found.values())


def index_results(results: list[Result]) -> dict[str, dict[int, Result]]:
    indexed = {name: {} for name in TARGETS}
    for result in results:
        indexed[result.name][result.season] = result
    return indexed


def validate_complete(indexed: dict[str, dict[int, Result]]) -> None:
    missing = []
    for name in sorted(TARGETS):
        for season in SEASONS:
            if season not in indexed[name]:
                missing.append(f"{name}:{season}")
    if missing:
        raise ValueError(
            "78G registry is missing required results: " + ", ".join(missing)
        )


def candidate_stats(
    indexed: dict[str, dict[int, Result]],
    candidate: str,
) -> dict[str, object]:
    baseline = indexed["recent_form_v1_baseline"]
    rows = indexed[candidate]

    score_deltas = [
        rows[season].selection_score - baseline[season].selection_score
        for season in SEASONS
    ]
    accuracy_deltas = [
        rows[season].winner_accuracy - baseline[season].winner_accuracy
        for season in SEASONS
    ]

    wins = sum(delta < 0 for delta in score_deltas)
    losses = sum(delta > 0 for delta in score_deltas)
    ties = len(score_deltas) - wins - losses

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
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "season_score_deltas": {
            str(season): delta
            for season, delta in zip(SEASONS, score_deltas, strict=True)
        },
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
            float(name.rsplit("_", 1)[-1]) if name != "recent_form_v1_baseline" else 0,
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

    # Prefer 5.25 when it is effectively tied with the numerical winner.
    center = "def_epa_trend_0525"
    if center in stats:
        gap = (
            stats[center]["mean_score_delta"]
            - best_stats["mean_score_delta"]
        )
        if gap <= 0.00015 and stats[center]["looso_improves_count"] >= 3:
            best = center

    return best, "PROVISIONAL_PASS"


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"Research registry not found: {REGISTRY}")

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    indexed = index_results(extract_results(payload))
    validate_complete(indexed)

    stats = {
        candidate: candidate_stats(indexed, candidate)
        for candidate in (
            "def_epa_trend_050",
            "def_epa_trend_0525",
            "def_epa_trend_055",
        )
    }

    winner, status = choose_candidate(stats)

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 78G DEFENSIVE EPA TREND ROBUSTNESS")
    print("=" * 96)
    for name, values in stats.items():
        print(
            f"{name:<20} "
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

    output = Path("data/reports/research/step78g_robustness.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "step": "78G",
                "status": status,
                "candidate": winner,
                "stats": stats,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(f"Report: {output.resolve()}")

    return 0 if status != "PARK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
