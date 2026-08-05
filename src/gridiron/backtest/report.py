"""Console and file reporting for historical backtests."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from gridiron.backtest.models import BacktestResult


def format_backtest_report(result: BacktestResult) -> str:
    """Return a readable console report."""
    lines = [
        "=" * 60,
        "                PROJECT GRIDIRON BACKTEST",
        "=" * 60,
        f"Season................... {result.season}",
        f"Model.................... {result.model_version}",
        f"Games evaluated.......... {result.games_evaluated}",
        f"Prediction coverage...... {result.prediction_coverage:.1%}",
        "-" * 60,
        f"Winner accuracy.......... {result.winner_accuracy:.1%}",
        f"Brier score.............. {result.brier_score:.4f}",
        f"Log loss................. {result.log_loss:.4f}",
        f"Margin MAE............... {result.margin_mae:.3f}",
        f"Margin RMSE.............. {result.margin_rmse:.3f}",
        f"Home-pick accuracy....... {result.home_accuracy:.1%}",
        f"Away-pick accuracy....... {result.away_accuracy:.1%}",
        "-" * 60,
        "Calibration",
    ]
    if not result.calibration:
        lines.append("No populated calibration buckets.")
    else:
        for bucket in result.calibration:
            lines.append(
                f"{bucket.lower_bound:.0%}-{bucket.upper_bound:.0%}: "
                f"n={bucket.games}, predicted={bucket.mean_probability:.1%}, "
                f"observed={bucket.observed_win_rate:.1%}"
            )
    lines.extend(
        [
            "-" * 60,
            f"Runtime.................. {result.runtime_seconds:.4f} s",
            "=" * 60,
        ]
    )
    return "\n".join(lines)


def print_backtest_report(result: BacktestResult) -> None:
    """Print one backtest report."""
    print(format_backtest_report(result))


def write_backtest_reports(result: BacktestResult, report_dir: Path) -> None:
    """Persist JSON and Markdown summaries."""
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"backtest_{result.season}_{result.model_version.replace(' ', '_')}"
    payload = asdict(result)
    (report_dir / f"{stem}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (report_dir / f"{stem}.md").write_text(
        "```text\n" + format_backtest_report(result) + "\n```\n",
        encoding="utf-8",
    )
