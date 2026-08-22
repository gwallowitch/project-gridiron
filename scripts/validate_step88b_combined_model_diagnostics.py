"""Step 88B — combined-model historical diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable
from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths

EXPECTED_FINGERPRINT = (
    "b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977"
)

SEASONS = (2022, 2023, 2024, 2025)

PROBABILITY_ALIASES = (
    "home_win_probability",
    "home_probability",
    "win_probability",
    "predicted_home_win_probability",
)

ACTUAL_HOME_WIN_ALIASES = (
    "home_win",
    "actual_home_win",
    "home_team_won",
)

HOME_SCORE_ALIASES = (
    "home_score",
    "home_points",
    "home_final_score",
)

AWAY_SCORE_ALIASES = (
    "away_score",
    "away_points",
    "away_final_score",
)

PREDICTED_MARGIN_ALIASES = (
    "predicted_margin",
    "home_margin_prediction",
    "predicted_home_margin",
    "model_margin",
)

ACTUAL_MARGIN_ALIASES = (
    "actual_margin",
    "home_margin",
    "margin",
)

GAME_ID_ALIASES = ("game_id",)


def _first_existing(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    available = set(columns)
    for alias in aliases:
        if alias in available:
            return alias
    return None


def _candidate_artifacts(paths: ProjectPaths, season: int) -> list[Path]:
    return [
        paths.backtest_file(season),
        paths.predictions_file(season),
        paths.root
        / "data"
        / "curated"
        / "research_predictions"
        / f"research_predictions_{season}.parquet",
        paths.root
        / "data"
        / "reports"
        / "research"
        / f"predictions_{season}.parquet",
    ]


def _load_game_level(paths: ProjectPaths, season: int) -> tuple[pl.DataFrame, Path]:
    for path in _candidate_artifacts(paths, season):
        if not path.exists():
            continue

        frame = pl.read_parquet(path)
        prob = _first_existing(frame.columns, PROBABILITY_ALIASES)
        if prob is not None:
            return frame, path

    searched = "\n".join(f"  - {p}" for p in _candidate_artifacts(paths, season))
    raise FileNotFoundError(
        f"No game-level prediction/backtest artifact with a home-win probability "
        f"column was found for {season}. Searched:\n{searched}"
    )


def _normalize_game_frame(
    frame: pl.DataFrame,
    schedule: pl.DataFrame,
) -> pl.DataFrame:
    prob_col = _first_existing(frame.columns, PROBABILITY_ALIASES)
    if prob_col is None:
        raise ValueError("Game-level artifact has no recognized probability column.")

    game_id_col = _first_existing(frame.columns, GAME_ID_ALIASES)
    if game_id_col is None:
        raise ValueError("Game-level artifact has no game_id column.")

    working = frame.rename(
        {
            prob_col: "model_home_win_probability",
            game_id_col: "game_id",
        }
    )

    actual_home_win_col = _first_existing(
        working.columns,
        ACTUAL_HOME_WIN_ALIASES,
    )

    if actual_home_win_col is not None:
        if actual_home_win_col != "actual_home_win":
            working = working.rename(
                {actual_home_win_col: "actual_home_win"}
            )
    else:
        home_score_col = _first_existing(
            working.columns,
            HOME_SCORE_ALIASES,
        )
        away_score_col = _first_existing(
            working.columns,
            AWAY_SCORE_ALIASES,
        )

        if home_score_col is not None and away_score_col is not None:
            working = working.with_columns(
                (
                    pl.col(home_score_col) > pl.col(away_score_col)
                )
                .cast(pl.Float64)
                .alias("actual_home_win")
            )
        else:
            schedule_home_score = _first_existing(
                schedule.columns,
                HOME_SCORE_ALIASES,
            )
            schedule_away_score = _first_existing(
                schedule.columns,
                AWAY_SCORE_ALIASES,
            )

            if schedule_home_score is None or schedule_away_score is None:
                raise ValueError(
                    "Could not derive actual_home_win from either the game-level "
                    "artifact or schedule scores."
                )

            outcomes = schedule.select(
                "game_id",
                (
                    pl.col(schedule_home_score)
                    > pl.col(schedule_away_score)
                )
                .cast(pl.Float64)
                .alias("actual_home_win"),
            )
            working = working.join(outcomes, on="game_id", how="left")

    predicted_margin_col = _first_existing(
        working.columns,
        PREDICTED_MARGIN_ALIASES,
    )
    actual_margin_col = _first_existing(
        working.columns,
        ACTUAL_MARGIN_ALIASES,
    )

    if predicted_margin_col is not None and predicted_margin_col != "predicted_margin":
        working = working.rename(
            {predicted_margin_col: "predicted_margin"}
        )

    if actual_margin_col is not None and actual_margin_col != "actual_margin":
        working = working.rename(
            {actual_margin_col: "actual_margin"}
        )

    if "actual_margin" not in working.columns:
        schedule_home_score = _first_existing(
            schedule.columns,
            HOME_SCORE_ALIASES,
        )
        schedule_away_score = _first_existing(
            schedule.columns,
            AWAY_SCORE_ALIASES,
        )
        if schedule_home_score is not None and schedule_away_score is not None:
            margins = schedule.select(
                "game_id",
                (
                    pl.col(schedule_home_score)
                    - pl.col(schedule_away_score)
                ).alias("actual_margin"),
            )
            working = working.join(margins, on="game_id", how="left")

    return (
        working
        .with_columns(
            pl.col("model_home_win_probability")
            .cast(pl.Float64)
            .clip(0.0, 1.0),
            pl.col("actual_home_win").cast(pl.Float64),
        )
        .filter(
            pl.col("model_home_win_probability").is_not_null()
            & pl.col("actual_home_win").is_not_null()
        )
    )


def _safe_log_loss(prob: float, actual: float) -> float:
    eps = 1e-15
    p = min(max(prob, eps), 1.0 - eps)
    return -(actual * math.log(p) + (1.0 - actual) * math.log(1.0 - p))


def _season_metrics(frame: pl.DataFrame) -> dict[str, float | int | None]:
    probs = frame["model_home_win_probability"].to_list()
    actuals = frame["actual_home_win"].to_list()

    n = len(probs)
    if n == 0:
        raise ValueError("No usable game rows.")

    predicted_winners = [1.0 if p >= 0.5 else 0.0 for p in probs]

    accuracy = sum(
        1 for pred, actual in zip(predicted_winners, actuals)
        if pred == actual
    ) / n

    brier = sum((p - y) ** 2 for p, y in zip(probs, actuals)) / n
    log_loss = sum(
        _safe_log_loss(p, y)
        for p, y in zip(probs, actuals)
    ) / n

    result: dict[str, float | int | None] = {
        "games": n,
        "winner_accuracy": accuracy,
        "brier_score": brier,
        "log_loss": log_loss,
        "mean_home_probability": sum(probs) / n,
        "home_pick_rate": sum(1 for p in probs if p >= 0.5) / n,
        "high_confidence_rate": sum(
            1 for p in probs if p >= 0.65 or p <= 0.35
        ) / n,
        "close_probability_rate": sum(
            1 for p in probs if 0.45 <= p <= 0.55
        ) / n,
    }

    if "predicted_margin" in frame.columns and "actual_margin" in frame.columns:
        margin = frame.filter(
            pl.col("predicted_margin").is_not_null()
            & pl.col("actual_margin").is_not_null()
        )
        if margin.height:
            err = (
                pl.col("predicted_margin").cast(pl.Float64)
                - pl.col("actual_margin").cast(pl.Float64)
            )
            margin_stats = margin.select(
                err.abs().mean().alias("mae"),
                (err.pow(2).mean().sqrt()).alias("rmse"),
            ).row(0, named=True)
            result["margin_mae"] = float(margin_stats["mae"])
            result["margin_rmse"] = float(margin_stats["rmse"])
        else:
            result["margin_mae"] = None
            result["margin_rmse"] = None
    else:
        result["margin_mae"] = None
        result["margin_rmse"] = None

    return result


def _calibration_buckets(frame: pl.DataFrame) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []

    for lo in [i / 10 for i in range(10)]:
        hi = lo + 0.1
        bucket = frame.filter(
            (pl.col("model_home_win_probability") >= lo)
            & (
                (pl.col("model_home_win_probability") < hi)
                if hi < 1.0
                else (pl.col("model_home_win_probability") <= hi)
            )
        )

        if bucket.height == 0:
            continue

        mean_prob = float(
            bucket["model_home_win_probability"].mean()
        )
        actual_rate = float(bucket["actual_home_win"].mean())

        rows.append(
            {
                "lower": lo,
                "upper": hi,
                "games": bucket.height,
                "mean_probability": mean_prob,
                "actual_home_win_rate": actual_rate,
                "calibration_error": actual_rate - mean_prob,
            }
        )

    return rows


def _split_metrics(frame: pl.DataFrame) -> dict[str, dict[str, float | int]]:
    splits = {
        "model_home_favorite": frame.filter(
            pl.col("model_home_win_probability") >= 0.5
        ),
        "model_away_favorite": frame.filter(
            pl.col("model_home_win_probability") < 0.5
        ),
        "high_confidence": frame.filter(
            (pl.col("model_home_win_probability") >= 0.65)
            | (pl.col("model_home_win_probability") <= 0.35)
        ),
        "close_probability": frame.filter(
            (pl.col("model_home_win_probability") >= 0.45)
            & (pl.col("model_home_win_probability") <= 0.55)
        ),
    }

    result: dict[str, dict[str, float | int]] = {}

    for name, subset in splits.items():
        if subset.height == 0:
            result[name] = {"games": 0}
            continue

        metrics = _season_metrics(subset)
        result[name] = {
            "games": int(metrics["games"]),
            "winner_accuracy": float(metrics["winner_accuracy"]),
            "brier_score": float(metrics["brier_score"]),
            "log_loss": float(metrics["log_loss"]),
        }

    return result


def _expected_calibration_error(
    buckets: list[dict[str, float | int]],
) -> float:
    total = sum(int(row["games"]) for row in buckets)
    if total == 0:
        return 0.0

    return sum(
        int(row["games"])
        * abs(float(row["calibration_error"]))
        for row in buckets
    ) / total


def _load_88a_fingerprint(root: Path) -> str:
    path = (
        root
        / "data"
        / "reports"
        / "research"
        / "step88a_locked_model_integrity.json"
    )
    if not path.exists():
        raise FileNotFoundError(
            "Step 88A integrity report is missing: "
            f"{path}"
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload["model"]["fingerprint_sha256"])


def build_report(root: Path) -> dict[str, object]:
    paths = ProjectPaths.from_root(root)
    fingerprint = _load_88a_fingerprint(paths.root)

    failures: list[str] = []
    warnings: list[str] = []

    if fingerprint != EXPECTED_FINGERPRINT:
        failures.append(
            "Step 88A model fingerprint does not match the locked contract."
        )

    seasons: dict[str, object] = {}
    normalized_frames: list[pl.DataFrame] = []

    for season in SEASONS:
        schedule_path = paths.schedule_file(season)
        if not schedule_path.exists():
            raise FileNotFoundError(schedule_path)

        schedule = pl.read_parquet(schedule_path)
        raw, artifact_path = _load_game_level(paths, season)
        frame = _normalize_game_frame(raw, schedule)
        normalized_frames.append(
            frame.with_columns(pl.lit(season).alias("_diag_season"))
        )

        metrics = _season_metrics(frame)
        calibration = _calibration_buckets(frame)

        seasons[str(season)] = {
            "artifact": str(artifact_path),
            "metrics": metrics,
            "splits": _split_metrics(frame),
            "calibration": calibration,
            "expected_calibration_error": _expected_calibration_error(
                calibration
            ),
        }

        if int(metrics["games"]) < 250:
            warnings.append(
                f"{season}: fewer than 250 usable game-level rows."
            )

    pooled = pl.concat(normalized_frames, how="diagonal_relaxed")
    pooled_metrics = _season_metrics(pooled)
    pooled_calibration = _calibration_buckets(pooled)

    accuracies = [
        float(seasons[str(season)]["metrics"]["winner_accuracy"])
        for season in SEASONS
    ]
    briers = [
        float(seasons[str(season)]["metrics"]["brier_score"])
        for season in SEASONS
    ]
    log_losses = [
        float(seasons[str(season)]["metrics"]["log_loss"])
        for season in SEASONS
    ]

    stability = {
        "accuracy_range": max(accuracies) - min(accuracies),
        "brier_range": max(briers) - min(briers),
        "log_loss_range": max(log_losses) - min(log_losses),
    }

    return {
        "step": "88B",
        "status": "PASS" if not failures else "FAIL",
        "fingerprint_sha256": fingerprint,
        "failures": failures,
        "warnings": warnings,
        "seasons": seasons,
        "pooled": {
            "metrics": pooled_metrics,
            "splits": _split_metrics(pooled),
            "calibration": pooled_calibration,
            "expected_calibration_error": _expected_calibration_error(
                pooled_calibration
            ),
        },
        "stability": stability,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 88B — Combined-Model Historical Diagnostics",
        "",
        f"Model fingerprint: `{report['fingerprint_sha256']}`",
        "",
        "## Season metrics",
        "",
        "| Season | Games | Accuracy | Brier | Log loss | MAE | RMSE | ECE |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for season, row in report["seasons"].items():
        m = row["metrics"]
        mae = "n/a" if m["margin_mae"] is None else f"{m['margin_mae']:.2f}"
        rmse = "n/a" if m["margin_rmse"] is None else f"{m['margin_rmse']:.2f}"
        lines.append(
            f"| {season} | {m['games']} | {m['winner_accuracy']:.1%} | "
            f"{m['brier_score']:.4f} | {m['log_loss']:.4f} | "
            f"{mae} | {rmse} | {row['expected_calibration_error']:.4f} |"
        )

    pooled = report["pooled"]["metrics"]
    lines.extend(
        [
            "",
            "## Pooled diagnostics",
            "",
            f"- Games: {pooled['games']}",
            f"- Winner accuracy: {pooled['winner_accuracy']:.1%}",
            f"- Brier score: {pooled['brier_score']:.4f}",
            f"- Log loss: {pooled['log_loss']:.4f}",
            (
                "- Expected calibration error: "
                f"{report['pooled']['expected_calibration_error']:.4f}"
            ),
            "",
            "## Stability",
            "",
            f"- Accuracy range: {report['stability']['accuracy_range']:.4f}",
            f"- Brier range: {report['stability']['brier_range']:.4f}",
            f"- Log-loss range: {report['stability']['log_loss_range']:.4f}",
            "",
            "## Gate",
            "",
        ]
    )

    if report["status"] == "PASS":
        lines.append(
            "**PASS** — locked-model historical diagnostics were generated "
            "without model drift."
        )
    else:
        lines.append("**FAIL**")
        lines.extend(f"- {item}" for item in report["failures"])

    if report["warnings"]:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/research"),
    )
    args = parser.parse_args()

    report = build_report(args.project_root)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "step88b_combined_model_diagnostics.json"
    md_path = args.output_dir / "step88b_combined_model_diagnostics.md"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 110)
    print("PROJECT GRIDIRON — STEP 88B COMBINED-MODEL HISTORICAL DIAGNOSTICS")
    print("=" * 110)
    print(f"Fingerprint............... {report['fingerprint_sha256']}")

    for season, row in report["seasons"].items():
        m = row["metrics"]
        print(
            f"{season}: games={m['games']}  "
            f"acc={m['winner_accuracy']:.1%}  "
            f"brier={m['brier_score']:.4f}  "
            f"logloss={m['log_loss']:.4f}  "
            f"ECE={row['expected_calibration_error']:.4f}"
        )

    pooled = report["pooled"]["metrics"]
    print("-" * 110)
    print(
        f"POOLED: games={pooled['games']}  "
        f"acc={pooled['winner_accuracy']:.1%}  "
        f"brier={pooled['brier_score']:.4f}  "
        f"logloss={pooled['log_loss']:.4f}  "
        f"ECE={report['pooled']['expected_calibration_error']:.4f}"
    )
    print(
        "STABILITY: "
        f"acc_range={report['stability']['accuracy_range']:.4f}  "
        f"brier_range={report['stability']['brier_range']:.4f}  "
        f"logloss_range={report['stability']['log_loss_range']:.4f}"
    )
    print("-" * 110)
    print(f"STATUS: {report['status']}")

    for warning in report["warnings"]:
        print(f"WARN: {warning}")

    for failure in report["failures"]:
        print(f"FAIL: {failure}")

    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 110)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
