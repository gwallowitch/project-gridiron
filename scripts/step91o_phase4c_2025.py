"""Step 91O Phase 4C — 2025 historical diagnostic breakdown.

This is diagnostic only. It does not modify the frozen candidate,
historical source data, protocol, manifest, ledger, or prospective evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT
    / "data"
    / "reports"
    / "backtests"
    / "phase4b_2025_frozen_core_three_diagnostic_rows.csv"
)

OUT_JSON = (
    ROOT / "data" / "reports" / "backtests" / "phase4c_2025_diagnostic_breakdown.json"
)

OUT_MD = (
    ROOT / "data" / "reports" / "backtests" / "phase4c_2025_diagnostic_breakdown.md"
)


def brier(prob: pl.Expr, actual: pl.Expr) -> pl.Expr:
    return (prob - actual) ** 2


def log_loss(prob: pl.Expr, actual: pl.Expr) -> pl.Expr:
    p = prob.clip(1e-15, 1 - 1e-15)
    return -(actual * p.log() + (1 - actual) * (1 - p).log())


def accuracy(
    predicted: pl.Expr,
    home_team: pl.Expr,
    away_team: pl.Expr,
    actual_home: pl.Expr,
) -> pl.Expr:
    expected_winner = pl.when(actual_home).then(home_team).otherwise(away_team)
    return (predicted == expected_winner).cast(pl.Float64)


def summarize_model(
    df: pl.DataFrame,
    probability: str,
    predicted: str,
) -> dict[str, float | int]:
    actual = pl.col("outcome") == pl.lit("HOME")

    values = df.select(
        accuracy(
            pl.col(predicted),
            pl.col("home_team"),
            pl.col("away_team"),
            actual,
        )
        .mean()
        .alias("accuracy"),
        brier(pl.col(probability), actual.cast(pl.Float64)).mean().alias("brier"),
        log_loss(pl.col(probability), actual.cast(pl.Float64)).mean().alias("log_loss"),
    ).row(0)

    return {
        "n": df.height,
        "accuracy": float(values[0]),
        "brier": float(values[1]),
        "log_loss": float(values[2]),
    }


def main() -> None:
    df = pl.read_csv(INPUT)

    required = {
        "game_id",
        "week",
        "away_team",
        "home_team",
        "outcome",
        "market_home_probability",
        "def_epa_trend_advantage",
        "candidate_home_probability",
        "candidate_predicted_winner",
        "market_predicted_winner",
        "legacy_v2_home_probability",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if df.height != 256:
        raise ValueError(
            f"Phase 4B diagnostic population changed: expected 256, got {df.height}"
        )

    df = df.with_columns(
        [
            (pl.col("outcome") == "HOME").alias("actual_home"),
            (
                pl.col("candidate_home_probability") - pl.col("market_home_probability")
            ).alias("candidate_market_delta"),
            (
                pl.col("candidate_predicted_winner")
                != pl.col("market_predicted_winner")
            ).alias("prediction_disagreement"),
            (pl.col("candidate_home_probability") >= 0.5).alias("candidate_home_pick"),
            (pl.col("market_home_probability") >= 0.5).alias("market_home_pick"),
        ]
    )

    # ------------------------------------------------------------------
    # Overall
    # ------------------------------------------------------------------

    tie_count = df.filter(pl.col("outcome") == "TIE").height
    if tie_count != 1:
        raise ValueError(f"Expected exactly one historical tie, got {tie_count}")

    input_rows = df.height
    if df.filter(
        ~pl.col("outcome").is_in(["HOME", "AWAY", "TIE"]) | pl.col("outcome").is_null()
    ).height:
        raise ValueError("Unknown outcome in diagnostic input")
    # All subsequent calculations share the same binary scoring population.
    df = df.filter(pl.col("outcome").is_in(["HOME", "AWAY"]))
    scoring_df = df

    if scoring_df.height != 255:
        raise ValueError(f"Expected 255 non-tied scoring rows, got {scoring_df.height}")

    overall = {
        "frozen_candidate": summarize_model(
            scoring_df,
            "candidate_home_probability",
            "candidate_predicted_winner",
        ),
        "core_three_market": summarize_model(
            scoring_df,
            "market_home_probability",
            "market_predicted_winner",
        ),
    }

    # Legacy v2 has no predicted-winner column in this diagnostic file,
    # so derive the winner mechanically from its home probability.
    legacy = df.with_columns(
        pl.when(pl.col("legacy_v2_home_probability") >= 0.5)
        .then(pl.col("home_team"))
        .otherwise(pl.col("away_team"))
        .alias("legacy_predicted_winner")
    )

    overall["legacy_v2"] = summarize_model(
        legacy.filter(pl.col("outcome") != "TIE"),
        "legacy_v2_home_probability",
        "legacy_predicted_winner",
    )

    # ------------------------------------------------------------------
    # Candidate vs market
    # ------------------------------------------------------------------

    disagreements = df.filter(pl.col("prediction_disagreement"))

    disagreement_result = {
        "count": disagreements.height,
        "rate": disagreements.height / df.height,
    }

    if disagreements.height:
        disagreement_result["candidate_correct"] = int(
            disagreements.select(
                (
                    pl.col("candidate_predicted_winner")
                    == pl.when(pl.col("actual_home"))
                    .then(pl.col("home_team"))
                    .otherwise(pl.col("away_team"))
                ).sum()
            ).item()
        )

        disagreement_result["market_correct"] = int(
            disagreements.select(
                (
                    pl.col("market_predicted_winner")
                    == pl.when(pl.col("actual_home"))
                    .then(pl.col("home_team"))
                    .otherwise(pl.col("away_team"))
                ).sum()
            ).item()
        )

    # ------------------------------------------------------------------
    # DEF EPA adjustment
    # ------------------------------------------------------------------

    adjustment = df.select(
        pl.col("candidate_market_delta").abs().mean().alias("mean_abs"),
        pl.col("candidate_market_delta").abs().median().alias("median_abs"),
        pl.col("candidate_market_delta").abs().max().alias("max_abs"),
        pl.col("candidate_market_delta").mean().alias("mean"),
        (pl.col("candidate_market_delta") > 0).sum().alias("positive"),
        (pl.col("candidate_market_delta") < 0).sum().alias("negative"),
        (pl.col("candidate_market_delta") == 0).sum().alias("zero"),
    ).row(0)

    adjustment_result = {
        "mean_absolute_probability_change": float(adjustment[0]),
        "median_absolute_probability_change": float(adjustment[1]),
        "maximum_absolute_probability_change": float(adjustment[2]),
        "mean_probability_change": float(adjustment[3]),
        "positive_adjustments": int(adjustment[4]),
        "negative_adjustments": int(adjustment[5]),
        "zero_adjustments": int(adjustment[6]),
    }

    # ------------------------------------------------------------------
    # Probability bands
    # ------------------------------------------------------------------

    def band_column(probability: str) -> pl.Expr:
        return (
            pl.when(pl.col(probability) < 0.5)
            .then(pl.lit("0%-50%"))
            .when(pl.col(probability) < 0.6)
            .then(pl.lit("50%-60%"))
            .when(pl.col(probability) < 0.7)
            .then(pl.lit("60%-70%"))
            .when(pl.col(probability) < 0.8)
            .then(pl.lit("70%-80%"))
            .when(pl.col(probability) < 0.9)
            .then(pl.lit("80%-90%"))
            .otherwise(pl.lit("90%-100%"))
        )

    candidate_bands = (
        df.with_columns(band_column("candidate_home_probability").alias("band"))
        .group_by("band")
        .agg(
            pl.len().alias("n"),
            pl.col("candidate_home_probability").mean().alias("predicted"),
            pl.col("actual_home").mean().alias("observed"),
        )
        .sort("band")
    )

    market_bands = (
        df.with_columns(band_column("market_home_probability").alias("band"))
        .group_by("band")
        .agg(
            pl.len().alias("n"),
            pl.col("market_home_probability").mean().alias("predicted"),
            pl.col("actual_home").mean().alias("observed"),
        )
        .sort("band")
    )

    # ------------------------------------------------------------------
    # Week-by-week
    # ------------------------------------------------------------------

    weekly = (
        df.with_columns(
            [
                (
                    pl.col("candidate_predicted_winner")
                    == pl.when(pl.col("actual_home"))
                    .then(pl.col("home_team"))
                    .otherwise(pl.col("away_team"))
                )
                .cast(pl.Float64)
                .alias("candidate_correct"),
                (
                    pl.col("market_predicted_winner")
                    == pl.when(pl.col("actual_home"))
                    .then(pl.col("home_team"))
                    .otherwise(pl.col("away_team"))
                )
                .cast(pl.Float64)
                .alias("market_correct"),
            ]
        )
        .group_by("week")
        .agg(
            pl.len().alias("n"),
            pl.col("candidate_correct").mean().alias("candidate_accuracy"),
            pl.col("market_correct").mean().alias("market_accuracy"),
            (
                pl.col("candidate_home_probability")
                - pl.col("actual_home").cast(pl.Float64)
            )
            .pow(2)
            .mean()
            .alias("candidate_brier"),
            (pl.col("market_home_probability") - pl.col("actual_home").cast(pl.Float64))
            .pow(2)
            .mean()
            .alias("market_brier"),
        )
        .sort("week")
    )

    # ------------------------------------------------------------------
    # Largest DEF EPA moves
    # ------------------------------------------------------------------

    largest_moves = (
        df.select(
            [
                "game_id",
                "week",
                "away_team",
                "home_team",
                "market_home_probability",
                "def_epa_trend_advantage",
                "candidate_home_probability",
                "candidate_market_delta",
                "market_predicted_winner",
                "candidate_predicted_winner",
                "outcome",
            ]
        )
        .with_columns(
            pl.col("candidate_market_delta").abs().alias("absolute_probability_change")
        )
        .sort("absolute_probability_change", descending=True)
        .head(20)
    )

    # ------------------------------------------------------------------
    # Serialize
    # ------------------------------------------------------------------

    result = {
        "classification": "HISTORICAL_DIAGNOSTIC_NOT_PROSPECTIVE_EVIDENCE",
        "season": 2025,
        "population": {
            "source": str(INPUT.relative_to(ROOT)),
            "rows": df.height,
            "input_rows": input_rows,
            "week_1_excluded": 16,
            "ties_excluded": 1,
        },
        "overall": overall,
        "candidate_vs_market": disagreement_result,
        "def_epa_adjustment": adjustment_result,
        "candidate_probability_bands": candidate_bands.to_dicts(),
        "market_probability_bands": market_bands.to_dicts(),
        "weekly": weekly.to_dicts(),
        "largest_def_epa_moves": largest_moves.to_dicts(),
        "interpretation_boundary": [
            "No model was fitted or recalibrated.",
            "The frozen candidate coefficients were unchanged.",
            "Historical market and EPA provenance limitations from Phase 4A remain unresolved.",
            "Results are diagnostic only and are not leakage-safe validation or prospective evidence.",
        ],
    }

    OUT_JSON.write_text(
        json.dumps(result, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    md = [
        "# Step 91O Phase 4C — 2025 Diagnostic Performance Breakdown",
        "",
        "**Classification: HISTORICAL DIAGNOSTIC — NOT PROSPECTIVE EVIDENCE**",
        "",
        "## Population",
        "",
        f"- Input diagnostic rows: {input_rows}",
        f"- Non-tied scoring rows (all calculations): {df.height}",
        "- Week 1 excluded: 16 (no prior-season DEF EPA feature)",
        "- Ties excluded: 1",
        "",
        "## Overall",
        "",
        "| Model | N | Accuracy | Brier | Log loss |",
        "|---|---:|---:|---:|---:|",
    ]

    for name, values in overall.items():
        md.append(
            f"| {name} | {values['n']} | "
            f"{values['accuracy']:.4f} | "
            f"{values['brier']:.4f} | "
            f"{values['log_loss']:.4f} |"
        )

    md.extend(
        [
            "",
            "## Candidate vs Core-Three Market",
            "",
            (
                f"- Prediction disagreements: {disagreement_result['count']} "
                f"({disagreement_result['rate']:.1%})"
            ),
        ]
    )

    if disagreements.height:
        md.extend(
            [
                f"- Candidate correct on disagreements: {disagreement_result['candidate_correct']}",
                f"- Market correct on disagreements: {disagreement_result['market_correct']}",
            ]
        )

    md.extend(
        [
            "",
            "## DEF EPA Adjustment",
            "",
            f"- Mean absolute probability change: {adjustment_result['mean_absolute_probability_change']:.6f}",
            f"- Median absolute probability change: {adjustment_result['median_absolute_probability_change']:.6f}",
            f"- Maximum absolute probability change: {adjustment_result['maximum_absolute_probability_change']:.6f}",
            f"- Positive adjustments: {adjustment_result['positive_adjustments']}",
            f"- Negative adjustments: {adjustment_result['negative_adjustments']}",
            f"- Zero adjustments: {adjustment_result['zero_adjustments']}",
            "",
            "## Candidate Probability Calibration",
            "",
            "| Band | N | Predicted | Observed |",
            "|---|---:|---:|---:|",
        ]
    )

    for row in candidate_bands.to_dicts():
        md.append(
            f"| {row['band']} | {row['n']} | "
            f"{row['predicted']:.4f} | {row['observed']:.4f} |"
        )

    md.extend(
        [
            "",
            "## Core-Three Market Calibration",
            "",
            "| Band | N | Predicted | Observed |",
            "|---|---:|---:|---:|",
        ]
    )

    for row in market_bands.to_dicts():
        md.append(
            f"| {row['band']} | {row['n']} | "
            f"{row['predicted']:.4f} | {row['observed']:.4f} |"
        )

    md.extend(
        [
            "",
            "## Weekly Accuracy",
            "",
            "| Week | N | Candidate Acc. | Market Acc. | Candidate Brier | Market Brier |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in weekly.to_dicts():
        md.append(
            f"| {row['week']} | {row['n']} | "
            f"{row['candidate_accuracy']:.4f} | "
            f"{row['market_accuracy']:.4f} | "
            f"{row['candidate_brier']:.4f} | "
            f"{row['market_brier']:.4f} |"
        )

    md.extend(
        [
            "",
            "## Largest DEF EPA Moves",
            "",
            "| Game | Week | Market P | DEF EPA | Candidate P | Delta | Outcome |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in largest_moves.to_dicts():
        md.append(
            f"| {row['game_id']} | {row['week']} | "
            f"{row['market_home_probability']:.4f} | "
            f"{row['def_epa_trend_advantage']:.4f} | "
            f"{row['candidate_home_probability']:.4f} | "
            f"{row['candidate_market_delta']:+.4f} | "
            f"{row['outcome']} |"
        )

    md.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- No model was fitted or recalibrated.",
            "- Frozen coefficients and residual cap were unchanged.",
            "- Historical market/EPA provenance limitations from Phase 4A remain unresolved.",
            "- This is diagnostic analysis only.",
            "- It is not leakage-safe validation or prospective evidence.",
        ]
    )

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("=" * 88)
    print("STEP 91O PHASE 4C — 2025 DIAGNOSTIC PERFORMANCE BREAKDOWN")
    print("=" * 88)
    print(f"Rows: {df.height}")
    print()
    print("MODEL                 N       ACC      BRIER    LOG LOSS")
    print("-" * 72)

    for name, values in overall.items():
        print(
            f"{name:22} {values['n']:3d}   "
            f"{values['accuracy']:.4f}   "
            f"{values['brier']:.4f}   "
            f"{values['log_loss']:.4f}"
        )

    print()
    print(
        "Candidate/market disagreements:",
        disagreement_result["count"],
        f"({disagreement_result['rate']:.1%})",
    )
    print(
        "Mean absolute DEF EPA probability adjustment:",
        f"{adjustment_result['mean_absolute_probability_change']:.6f}",
    )
    print()
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()
