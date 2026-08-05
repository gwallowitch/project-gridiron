"""Console reporting for prediction experiments."""

from __future__ import annotations

from gridiron.experiments.models import ExperimentResult


def format_experiment_report(results: list[ExperimentResult]) -> str:
    """Format ranked experiment results for console output."""
    if not results:
        raise ValueError("Cannot format an empty experiment result set.")

    lines = [
        "=" * 76,
        "                    PROJECT GRIDIRON EXPERIMENTS",
        "=" * 76,
        f"Season: {results[0].season}",
        f"Experiments: {len(results)}",
        "-" * 76,
        "Rank  Experiment            Acc.    Brier    LogLoss   RMSE    Score",
        "-" * 76,
    ]
    for rank, result in enumerate(results, start=1):
        lines.append(
            f"{rank:>4}  {result.name:<20} "
            f"{result.winner_accuracy:>6.1%}  "
            f"{result.brier_score:>7.4f}  "
            f"{result.log_loss:>8.4f}  "
            f"{result.margin_rmse:>6.2f}  "
            f"{result.selection_score:>7.4f}"
        )
    lines.extend(
        [
            "-" * 76,
            f"Recommended configuration: {results[0].name}",
            "Lower selection score is better.",
            "=" * 76,
        ]
    )
    return "\n".join(lines)


def print_experiment_report(results: list[ExperimentResult]) -> None:
    """Print a ranked experiment report."""
    print(format_experiment_report(results))
