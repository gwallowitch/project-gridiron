"""Audit Week 2 frozen DEF EPA input readiness without making predictions."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.features.recent_form.features import build_recent_form_features
from scripts import gridiron_game_day as game_day
from scripts.gridiron_operational_prediction import DEF_EPA_COEFFICIENT

REQUIRED_PBP = {"game_id", "season", "week", "posteam", "defteam", "play_type", "epa"}
PROVENANCE = "computed frozen feature from valid 2026 Week 1 nflverse data"


class Week2ReadinessError(ValueError):
    """The Week 2 audit cannot establish the frozen input contract."""


def load_current_pbp(season: int) -> pl.DataFrame:
    """Preserve the operational clear-before-load freshness path."""
    try:
        nfl.clear_cache(f"play_by_play_{season}")
        return nfl.load_pbp(season)
    except Exception as exc:
        raise Week2ReadinessError(
            f"could not refresh/load nflverse {season} play-by-play: {exc}"
        ) from exc


def audit_week2(
    schedule_path: Path | str = game_day.SCHEDULE_PATH,
    *,
    pbp_loader: Callable[[int], pl.DataFrame] = load_current_pbp,
) -> tuple[dict[str, Any], ...]:
    schedule = tuple(
        game
        for game in game_day.load_schedule(schedule_path)
        if game.get("season") == 2026
        and game.get("season_type") == "REG"
        and game.get("week") == 2
    )
    if not schedule:
        raise Week2ReadinessError("canonical schedule contains no 2026 REG Week 2 games")
    pbp = pbp_loader(2026)
    if not isinstance(pbp, pl.DataFrame):
        raise Week2ReadinessError("nflverse loader did not return a Polars DataFrame")
    missing = REQUIRED_PBP.difference(pbp.columns)
    if missing:
        raise Week2ReadinessError("nflverse play-by-play missing: " + ", ".join(sorted(missing)))

    # Exact season and immediately prior week are selected before the frozen builder.
    week1 = pbp.filter((pl.col("season") == 2026) & (pl.col("week") == 1))
    if week1.is_empty():
        raise Week2ReadinessError("2026 Week 1 play-by-play is unavailable")
    schedule_frame = pl.DataFrame(
        {
            field: [game[field] for game in schedule]
            for field in ("game_id", "season", "week", "home_team", "away_team")
        }
    )
    try:
        features = build_recent_form_features(schedule_frame, week1)
    except (ValueError, pl.exceptions.PolarsError) as exc:
        raise Week2ReadinessError(f"frozen feature builder failed: {exc}") from exc
    by_game = {row["game_id"]: row for row in features.to_dicts()}
    output = []
    for game in schedule:
        row = by_game.get(game["game_id"])
        if row is None:
            raise Week2ReadinessError("frozen feature builder lost schedule identity")
        home_available = row["home_def_epa_improvement"] is not None
        away_available = row["away_def_epa_improvement"] is not None
        ready = home_available and away_available
        reason = ""
        value: float | None = None
        home_improvement: float | None = None
        away_improvement: float | None = None
        if not home_available:
            reason = "HOME_WEEK1_DEF_EPA_MISSING"
        elif not away_available:
            reason = "AWAY_WEEK1_DEF_EPA_MISSING"
        else:
            home_improvement = float(row["home_def_epa_improvement"])
            away_improvement = float(row["away_def_epa_improvement"])
            value = float(row["def_epa_trend_advantage"])
            if not all(math.isfinite(item) for item in (home_improvement, away_improvement, value)):
                ready, reason = False, "NONFINITE_FROZEN_FEATURE"
            elif not all(math.isclose(item, 0.0, abs_tol=1e-12) for item in (home_improvement, away_improvement, value)):
                ready, reason = False, "WEEK2_COMPUTED_ZERO_INVARIANT_FAILED"
            else:
                reason = "COMPUTED_ZERO_FROM_VALID_WEEK1_DATA"
        output.append(
            {
                "game": game["game_id"],
                "home": game["home_team"],
                "away": game["away_team"],
                "kickoff": game["kickoff_at"],
                "week1_home_def_epa_available": home_available,
                "week1_away_def_epa_available": away_available,
                "home_def_epa_improvement": home_improvement,
                "away_def_epa_improvement": away_improvement,
                "def_epa_input_status": "READY" if ready else "NOT_READY",
                "def_epa_trend_advantage": value,
                "provenance": PROVENANCE if ready else None,
                "reason": reason,
            }
        )
    return tuple(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", type=Path, default=game_day.SCHEDULE_PATH)
    args = parser.parse_args(argv)
    try:
        rows = audit_week2(args.schedule)
    except (Week2ReadinessError, game_day.GameDayInputError, OSError) as exc:
        print(f"WEEK 2 DEF EPA READINESS: NOT_READY — {exc}", file=sys.stderr)
        return 2
    print("WEEK 2 DEF EPA OPERATIONAL READINESS — NO MODEL RECOMMENDATION")
    print(f"Frozen DEF EPA coefficient: {DEF_EPA_COEFFICIENT:+.6f}")
    print(f"Week 2 source: {PROVENANCE} (not the Week 1 explicit neutral fallback)")
    print("GAME | HOME | AWAY | KICKOFF | HOME_W1 | AWAY_W1 | STATUS | VALUE | REASON")
    for row in rows:
        value = "—" if row["def_epa_trend_advantage"] is None else f"{row['def_epa_trend_advantage']:+.6f}"
        print(
            f"{row['game']} | {row['home']} | {row['away']} | {row['kickoff']} | "
            f"{row['week1_home_def_epa_available']} | {row['week1_away_def_epa_available']} | "
            f"{row['def_epa_input_status']} | {value} | {row['reason']}"
        )
    return 0 if all(row["def_epa_input_status"] == "READY" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
