"""Leakage-safe turnover-regression features derived from prior games."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {"game_id", "season", "week", "home_team", "away_team"}
_REQUIRED_PBP = {"game_id", "season", "week", "posteam", "defteam", "interception", "fumble_lost"}


def _require(frame: pl.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(sorted(missing))}")


def build_turnover_features(schedule: pl.DataFrame, pbp: pl.DataFrame) -> pl.DataFrame:
    """Build pregame turnover features using games from strictly earlier weeks.

    Interceptions are retained as the more repeatable turnover component.
    Lost fumbles are tracked separately so later research can regress the
    higher-variance fumble component rather than treating all turnovers alike.
    """
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")
    _require(pbp, _REQUIRED_PBP, "Play-by-play")

    games = (
        pbp.group_by(["season", "week", "game_id", "posteam"])
        .agg(
            pl.col("interception").fill_null(0).sum().cast(pl.Float64).alias("interceptions_thrown"),
            pl.col("fumble_lost").fill_null(0).sum().cast(pl.Float64).alias("fumbles_lost"),
        )
        .with_columns(
            (pl.col("interceptions_thrown") + pl.col("fumbles_lost")).alias("turnovers_committed")
        )
    )

    rows: list[dict[str, object]] = []
    for game in schedule.sort(["season", "week", "game_id"]).iter_rows(named=True):
        season = int(game["season"])
        week = int(game["week"])
        result: dict[str, object] = {
            "game_id": game["game_id"],
            "season": season,
            "week": week,
            "home_team": game["home_team"],
            "away_team": game["away_team"],
        }

        for side in ("home", "away"):
            team = game[f"{side}_team"]
            history = games.filter(
                (pl.col("season") == season)
                & (pl.col("week") < week)
                & (pl.col("posteam") == team)
            )
            known = history.height > 0
            result[f"{side}_turnover_known"] = known
            result[f"{side}_turnover_history_games"] = history.height

            if known:
                result[f"{side}_interceptions_thrown_pg"] = float(
                    history["interceptions_thrown"].mean()
                )
                result[f"{side}_fumbles_lost_pg"] = float(history["fumbles_lost"].mean())
                result[f"{side}_turnovers_committed_pg"] = float(
                    history["turnovers_committed"].mean()
                )
            else:
                result[f"{side}_interceptions_thrown_pg"] = None
                result[f"{side}_fumbles_lost_pg"] = None
                result[f"{side}_turnovers_committed_pg"] = None

        if result["home_turnover_known"] and result["away_turnover_known"]:
            result["interception_rate_difference"] = (
                result["away_interceptions_thrown_pg"] - result["home_interceptions_thrown_pg"]
            )
            result["fumble_lost_rate_difference"] = (
                result["away_fumbles_lost_pg"] - result["home_fumbles_lost_pg"]
            )
            result["turnover_rate_difference"] = (
                result["away_turnovers_committed_pg"] - result["home_turnovers_committed_pg"]
            )
        else:
            result["interception_rate_difference"] = None
            result["fumble_lost_rate_difference"] = None
            result["turnover_rate_difference"] = None

        rows.append(result)

    return pl.DataFrame(rows)
