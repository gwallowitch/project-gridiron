"""Step 87A — leakage-safe rolling play-consistency features."""

from __future__ import annotations

import polars as pl

_REQUIRED_SCHEDULE = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
}

_REQUIRED_PBP = {
    "game_id",
    "posteam",
    "defteam",
    "yards_gained",
    "epa",
    "pass_attempt",
    "rush_attempt",
}


def _require(
    frame: pl.DataFrame,
    required: set[str],
    label: str,
) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _team_game_consistency(pbp: pl.DataFrame) -> pl.DataFrame:
    """Aggregate team offensive/defensive consistency by game."""
    _require(pbp, _REQUIRED_PBP, "PBP")

    plays = (
        pbp.filter(
            pl.col("posteam").is_not_null()
            & pl.col("defteam").is_not_null()
            & pl.col("epa").is_not_null()
            & (
                (pl.col("pass_attempt") == 1.0)
                | (pl.col("rush_attempt") == 1.0)
            )
        )
        .with_columns(
            (pl.col("epa") > 0.0)
            .cast(pl.Float64)
            .alias("offensive_success"),
            (pl.col("epa") <= 0.0)
            .cast(pl.Float64)
            .alias("defensive_success_prevention"),
            (pl.col("yards_gained") < 0.0)
            .cast(pl.Float64)
            .alias("offensive_negative_play"),
            (pl.col("yards_gained") < 0.0)
            .cast(pl.Float64)
            .alias("defensive_negative_play_forced"),
        )
    )

    offense = (
        plays.group_by(
            "game_id",
            pl.col("posteam").alias("team"),
        )
        .agg(
            pl.col("offensive_success")
            .mean()
            .alias("off_success_rate"),
            pl.col("offensive_negative_play")
            .mean()
            .alias("off_negative_play_rate"),
        )
    )

    defense = (
        plays.group_by(
            "game_id",
            pl.col("defteam").alias("team"),
        )
        .agg(
            pl.col("defensive_success_prevention")
            .mean()
            .alias("def_success_prevention_rate"),
            pl.col("defensive_negative_play_forced")
            .mean()
            .alias("def_negative_play_forced_rate"),
        )
    )

    return offense.join(
        defense,
        on=["game_id", "team"],
        how="full",
        coalesce=True,
    )


def build_play_consistency_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
    *,
    rolling_games: int = 4,
) -> pl.DataFrame:
    """Build prior-game rolling play-consistency matchup features."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    team_game = _team_game_consistency(pbp)

    long_schedule = pl.concat(
        [
            schedule.select(
                "game_id",
                "season",
                "week",
                pl.col("home_team").alias("team"),
                pl.lit("home").alias("side"),
            ),
            schedule.select(
                "game_id",
                "season",
                "week",
                pl.col("away_team").alias("team"),
                pl.lit("away").alias("side"),
            ),
        ]
    )

    history = (
        long_schedule.join(
            team_game,
            on=["game_id", "team"],
            how="left",
        )
        .sort(["team", "season", "week", "game_id"])
        .with_columns(
            pl.col("off_success_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_off_success_rate"),
            pl.col("def_success_prevention_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_def_success_prevention_rate"),
            pl.col("off_negative_play_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_off_negative_play_rate"),
            pl.col("def_negative_play_forced_rate")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_def_negative_play_forced_rate"),
            pl.col("off_success_rate")
            .shift(1)
            .is_not_null()
            .over(["team", "season"])
            .alias("play_consistency_known"),
        )
    )

    home = (
        history.filter(pl.col("side") == "home")
        .select(
            "game_id",
            pl.col("pregame_off_success_rate")
            .alias("home_off_success_rate"),
            pl.col("pregame_def_success_prevention_rate")
            .alias("home_def_success_prevention_rate"),
            pl.col("pregame_off_negative_play_rate")
            .alias("home_off_negative_play_rate"),
            pl.col("pregame_def_negative_play_forced_rate")
            .alias("home_def_negative_play_forced_rate"),
            pl.col("play_consistency_known")
            .alias("home_play_consistency_known"),
        )
    )

    away = (
        history.filter(pl.col("side") == "away")
        .select(
            "game_id",
            pl.col("pregame_off_success_rate")
            .alias("away_off_success_rate"),
            pl.col("pregame_def_success_prevention_rate")
            .alias("away_def_success_prevention_rate"),
            pl.col("pregame_off_negative_play_rate")
            .alias("away_off_negative_play_rate"),
            pl.col("pregame_def_negative_play_forced_rate")
            .alias("away_def_negative_play_forced_rate"),
            pl.col("play_consistency_known")
            .alias("away_play_consistency_known"),
        )
    )

    return (
        schedule.select(
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
        )
        .join(home, on="game_id", how="left")
        .join(away, on="game_id", how="left")
        .with_columns(
            (
                pl.col("home_off_success_rate")
                - pl.col("away_off_success_rate")
            ).alias("off_success_rate_advantage"),
            (
                pl.col("home_def_success_prevention_rate")
                - pl.col("away_def_success_prevention_rate")
            ).alias("def_success_prevention_advantage"),
            (
                (
                    pl.col("home_off_success_rate")
                    + pl.col("home_def_success_prevention_rate")
                )
                - (
                    pl.col("away_off_success_rate")
                    + pl.col("away_def_success_prevention_rate")
                )
            ).alias("success_rate_matchup_advantage"),
            (
                (
                    pl.col("away_off_negative_play_rate")
                    + pl.col("home_def_negative_play_forced_rate")
                )
                - (
                    pl.col("home_off_negative_play_rate")
                    + pl.col("away_def_negative_play_forced_rate")
                )
            ).alias("negative_play_matchup_advantage"),
        )
    )
