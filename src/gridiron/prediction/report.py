"""Console reporting for weekly predictions."""

from __future__ import annotations

import polars as pl


def format_prediction_report(frame: pl.DataFrame, *, week: int) -> str:
    """Format one week's prediction slate for the console."""
    slate = frame.filter(pl.col("week") == week).sort("game_id")
    if slate.height == 0:
        raise ValueError(f"No predictions found for week {week}.")

    lines = [
        "=" * 60,
        "PROJECT GRIDIRON PREDICTIONS".center(60),
        "=" * 60,
        f"Week {week}",
        "",
    ]
    for row in slate.iter_rows(named=True):
        favorite = row["predicted_winner"]
        margin = abs(row["expected_home_margin"])
        lines.extend(
            [
                f"{row['away_team']} @ {row['home_team']}",
                f"Pick: {favorite} by {margin:.1f}",
                (
                    f"Home win: {row['home_win_probability']:.1%} | "
                    f"Away win: {row['away_win_probability']:.1%}"
                ),
                f"Confidence: {row['confidence'].title()}",
                "-" * 60,
            ]
        )
    return "\n".join(lines)


def print_prediction_report(frame: pl.DataFrame, *, week: int) -> None:
    """Print one week's prediction slate."""
    print(format_prediction_report(frame, week=week))
