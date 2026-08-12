"""Team/week and game-level injury availability features."""

from __future__ import annotations

import polars as pl


def aggregate_team_week_injuries(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    """Aggregate timestamp-eligible player reports by team and week."""
    eligible = frame.filter(pl.col("source_timestamp_known"))

    if eligible.height == 0:
        return _empty_team_week_frame()

    latest = (
        eligible.sort("source_modified_at")
        .group_by(
            ["season", "week", "team", "gsis_id"],
            maintain_order=True,
        )
        .last()
    )

    return (
        latest.group_by(["season", "week", "team"])
        .agg(
            pl.col("player_injury_severity")
            .sum()
            .alias("injury_score"),
            (pl.col("player_injury_severity") > 0)
            .sum()
            .cast(pl.UInt32)
            .alias("affected_players"),
            (pl.col("report_status") == "Out")
            .sum()
            .cast(pl.UInt32)
            .alias("out_players"),
            pl.col("has_injury_report")
            .sum()
            .cast(pl.UInt32)
            .alias("injury_report_count"),
        )
        .sort(["season", "week", "team"])
    )


def build_game_injury_features(
    schedule: pl.DataFrame,
    injuries: pl.DataFrame,
) -> pl.DataFrame:
    """Build conservative pregame injury features for scheduled games."""
    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
    }
    missing = required.difference(schedule.columns)
    if missing:
        raise ValueError(
            "Schedule is missing columns: "
            + ", ".join(sorted(missing))
        )

    has_kickoff = "kickoff_at" in schedule.columns
    records = injuries.filter(pl.col("source_timestamp_known"))

    if has_kickoff:
        game_teams = pl.concat(
            [
                schedule.select(
                    "season",
                    "week",
                    pl.col("home_team").alias("team"),
                    "kickoff_at",
                ),
                schedule.select(
                    "season",
                    "week",
                    pl.col("away_team").alias("team"),
                    "kickoff_at",
                ),
            ]
        )

        joined = game_teams.join(
            records,
            on=["season", "week", "team"],
            how="left",
        )

        records = (
            joined.filter(
                pl.col("source_modified_at")
                < pl.col("kickoff_at")
            )
            .select(
                [
                    column
                    for column in injuries.columns
                    if column in joined.columns
                ]
            )
        )

    team_week = aggregate_team_week_injuries(records)

    home = team_week.select(
        "season",
        "week",
        pl.col("team").alias("home_team"),
        pl.col("injury_score").alias("home_injury_score"),
        pl.col("affected_players").alias(
            "home_affected_players"
        ),
        pl.col("out_players").alias("home_out_players"),
        pl.col("injury_report_count").alias(
            "home_injury_report_count"
        ),
    )
    away = team_week.select(
        "season",
        "week",
        pl.col("team").alias("away_team"),
        pl.col("injury_score").alias("away_injury_score"),
        pl.col("affected_players").alias(
            "away_affected_players"
        ),
        pl.col("out_players").alias("away_out_players"),
        pl.col("injury_report_count").alias(
            "away_injury_report_count"
        ),
    )

    source_timestamp_available = (
        injuries.filter(pl.col("source_timestamp_known")).height > 0
    )

    return (
        schedule.select(
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
        )
        .join(
            home,
            on=["season", "week", "home_team"],
            how="left",
            validate="m:1",
        )
        .join(
            away,
            on=["season", "week", "away_team"],
            how="left",
            validate="m:1",
        )
        .with_columns(
            pl.col("home_injury_score").fill_null(0.0),
            pl.col("away_injury_score").fill_null(0.0),
            pl.col("home_affected_players").fill_null(0),
            pl.col("away_affected_players").fill_null(0),
            pl.col("home_out_players").fill_null(0),
            pl.col("away_out_players").fill_null(0),
            pl.col("home_injury_report_count").fill_null(0),
            pl.col("away_injury_report_count").fill_null(0),
        )
        .with_columns(
            (
                pl.col("home_injury_score")
                - pl.col("away_injury_score")
            ).alias("injury_score_difference"),
            (
                pl.col("home_injury_report_count") > 0
            ).alias("home_injury_known"),
            (
                pl.col("away_injury_report_count") > 0
            ).alias("away_injury_known"),
            pl.lit(
                has_kickoff and source_timestamp_available
            ).alias("kickoff_guard_applied"),
            pl.lit(source_timestamp_available).alias(
                "source_timestamp_available"
            ),
        )
        .sort(["season", "week", "game_id"])
    )


def _empty_team_week_frame() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "season": pl.Int32,
            "week": pl.Int32,
            "team": pl.String,
            "injury_score": pl.Float64,
            "affected_players": pl.UInt32,
            "out_players": pl.UInt32,
            "injury_report_count": pl.UInt32,
        }
    )
