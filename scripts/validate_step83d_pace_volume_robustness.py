"""Step 83D leave-one-season-out robustness validation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

REGISTRY = Path("data/reports/research/research_registry.json")
OUTPUT = Path("data/reports/research/step83d_pace_volume_robustness.json")
BASELINE = "pace_volume_v1_baseline"

CANDIDATES = (
    "pace_volume_0010",
    "pace_volume_0015",
    "pace_volume_0020",
    "pace_volume_0025",
    "pace_volume_0030",
    "pace_volume_0035",
)


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _name(row):
    return row.get("name") or row.get("experiment") or row.get("experiment_name")


def _season(row):
    value = row.get("season")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _score(row):
    for key in ("selection_score", "score", "aggregate_score"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def extract_rows(payload):
    rows = []
    seen = set()
    for row in _walk(payload):
        name = _name(row)
        season = _season(row)
        score = _score(row)
        if name is None or season is None or score is None:
            continue
        if name != BASELINE and name not in CANDIDATES:
            continue

        key = (season, name, score)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "season": season,
                "name": name,
                "selection_score": score,
            }
        )
    return rows


def evaluate(rows):
    seasons = sorted({row["season"] for row in rows})
    by_key = {
        (row["season"], row["name"]): row["selection_score"]
        for row in rows
    }

    if len(seasons) < 4:
        raise ValueError(f"Expected four seasons, found {seasons}.")

    for season in seasons:
        if (season, BASELINE) not in by_key:
            raise ValueError(f"Missing baseline for season {season}.")

    results = []
    for candidate in CANDIDATES:
        values = []
        season_deltas = []
        for season in seasons:
            key = (season, candidate)
            if key not in by_key:
                raise ValueError(f"Missing {candidate} for season {season}.")
            delta = by_key[key] - by_key[(season, BASELINE)]
            values.append(delta)
            season_deltas.append({"season": season, "delta": delta})

        looso = []
        for omitted in seasons:
            kept = [
                item["delta"]
                for item in season_deltas
                if item["season"] != omitted
            ]
            looso.append(
                {
                    "omitted_season": omitted,
                    "mean_delta": mean(kept),
                }
            )

        results.append(
            {
                "candidate": candidate,
                "mean_delta": mean(values),
                "season_wins": sum(value < 0.0 for value in values),
                "season_losses": sum(value > 0.0 for value in values),
                "season_ties": sum(value == 0.0 for value in values),
                "looso_wins": sum(
                    item["mean_delta"] < 0.0
                    for item in looso
                ),
                "looso_total": len(looso),
                "worst_looso_delta": max(
                    item["mean_delta"]
                    for item in looso
                ),
                "season_deltas": season_deltas,
                "looso": looso,
            }
        )

    results.sort(
        key=lambda row: (
            -row["looso_wins"],
            row["worst_looso_delta"],
            row["mean_delta"],
            row["candidate"],
        )
    )

    candidate = results[0]
    if (
        candidate["mean_delta"] < 0.0
        and candidate["looso_wins"] == candidate["looso_total"]
        and candidate["worst_looso_delta"] < 0.0
    ):
        status = "PROVISIONAL_PASS"
    else:
        status = "REJECT"

    return {
        "step": "83D",
        "baseline": BASELINE,
        "seasons": seasons,
        "results": results,
        "candidate": candidate["candidate"],
        "status": status,
    }


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    report = evaluate(extract_rows(payload))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("=" * 96)
    print("PROJECT GRIDIRON — STEP 83D PACE-VOLUME ROBUSTNESS")
    print("=" * 96)
    for row in report["results"]:
        print(
            f"{row['candidate']:<18} "
            f"MeanDelta={row['mean_delta']:+.7f}  "
            f"SeasonWins={row['season_wins']}/{len(report['seasons'])}  "
            f"LOOSO={row['looso_wins']}/{row['looso_total']}  "
            f"WorstLOOSO={row['worst_looso_delta']:+.7f}"
        )
    print("-" * 96)
    print(f"Candidate................ {report['candidate']}")
    print(f"Status................... {report['status']}")
    print(f"Report: {OUTPUT.resolve()}")
    print("=" * 96)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
