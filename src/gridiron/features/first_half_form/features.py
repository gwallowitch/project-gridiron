"""Step 85A â€” leakage-safe rolling first-half form features."""

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
    "qtr",
    "epa",
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


def _team_game_first_half(pbp: pl.DataFrame) -> pl.DataFrame:
    """Aggregate team first-half offensive/defensive EPA by game."""
    _require(pbp, _REQUIRED_PBP, "PBP")

    first_half = pbp.filter(
        pl.col("qtr").is_in([1, 2])
        & pl.col("epa").is_not_null()
    )

    offense = (
        first_half.filter(pl.col("posteam").is_not_null())
        .group_by("game_id", pl.col("posteam").alias("team"))
        .agg(
            pl.col("epa").mean().alias("first_half_off_epa_per_play"),
            pl.len().alias("first_half_off_plays"),
        )
    )

    defense = (
        first_half.filter(pl.col("defteam").is_not_null())
        .group_by("game_id", pl.col("defteam").alias("team"))
        .agg(
            (-pl.col("epa").mean()).alias("first_half_def_epa_advantage"),
            pl.len().alias("first_half_def_plays"),
        )
    )

    return offense.join(
        defense,
        on=["game_id", "team"],
        how="full",
        coalesce=True,
    )


def build_first_half_form_features(
    schedule: pl.DataFrame,
    pbp: pl.DataFrame,
    *,
    rolling_games: int = 4,
) -> pl.DataFrame:
    """Build prior-game rolling first-half form, excluding current game."""
    _require(schedule, _REQUIRED_SCHEDULE, "Schedule")

    team_game = _team_game_first_half(pbp)

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
            pl.col("first_half_off_epa_per_play")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_first_half_off_epa"),
            pl.col("first_half_def_epa_advantage")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_first_half_def_epa"),
            pl.col("first_half_off_plays")
            .shift(1)
            .rolling_mean(
                window_size=rolling_games,
                min_samples=1,
            )
            .over(["team", "season"])
            .alias("pregame_first_half_play_volume"),
            pl.col("first_half_off_epa_per_play")
            .shift(1)
            .is_not_null()
            .over(["team", "season"])
            .alias("first_half_form_known"),
        )
    )

    home = (
        history.filter(pl.col("side") == "home")
        .select(
            "game_id",
            pl.col("pregame_first_half_off_epa")
            .alias("home_first_half_off_epa"),
            pl.col("pregame_first_half_def_epa")
            .alias("home_first_half_def_epa"),
            pl.col("pregame_first_half_play_volume")
            .alias("home_first_half_play_volume"),
            pl.col("first_half_form_known")
            .alias("home_first_half_form_known"),
        )
    )

    away = (
        history.filter(pl.col("side") == "away")
        .select(
            "game_id",
            pl.col("pregame_first_half_off_epa")
            .alias("away_first_half_off_epa"),
            pl.col("pregame_first_half_def_epa")
            .alias("away_first_half_def_epa"),
            pl.col("pregame_first_half_play_volume")
            .alias("away_first_half_play_volume"),
            pl.col("first_half_form_known")
            .alias("away_first_half_form_known"),
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
                pl.col("home_first_half_off_epa")
                - pl.col("away_first_half_off_epa")
            ).alias("first_half_off_epa_advantage"),
            (
                pl.col("home_first_half_def_epa")
                - pl.col("away_first_half_def_epa")
            ).alias("first_half_def_epa_advantage"),
            (
                pl.col("home_first_half_play_volume")
                - pl.col("away_first_half_play_volume")
            ).alias("first_half_play_volume_advantage"),
        )
    )


