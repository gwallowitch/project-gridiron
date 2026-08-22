"""Step 88D â€” calibration robustness and selection."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

EXPECTED_FINGERPRINT = (
    "b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977"
)
SEASONS = (2022, 2023, 2024, 2025)
CANDIDATES = ("temperature", "logistic")


def _load_88c_module(root: Path):
    path = root / "scripts" / "validate_step88c_locked_model_calibration.py"
    if not path.exists():
        raise FileNotFoundError(
            f"Step 88C validator is required for 88D: {path}"
        )

    spec = importlib.util.spec_from_file_location("_step88c_for_88d", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")

    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_88c_report(root: Path) -> dict[str, object]:
    path = (
        root
        / "data"
        / "reports"
        / "research"
        / "step88c_locked_model_calibration_research.json"
    )
    if not path.exists():
        raise FileNotFoundError(
            f"Step 88C report is required for 88D: {path}"
        )

    return json.loads(path.read_text(encoding="utf-8"))


def _parameter_stats(
    folds: list[dict[str, object]],
) -> dict[str, float]:
    intercepts = np.asarray(
        [float(row["parameters"]["intercept"]) for row in folds],
        dtype=float,
    )
    slopes = np.asarray(
        [float(row["parameters"]["slope"]) for row in folds],
        dtype=float,
    )

    return {
        "intercept_mean": float(intercepts.mean()),
        "intercept_std": float(intercepts.std(ddof=0)),
        "intercept_range": float(intercepts.max() - intercepts.min()),
        "slope_mean": float(slopes.mean()),
        "slope_std": float(slopes.std(ddof=0)),
        "slope_range": float(slopes.max() - slopes.min()),
    }


def _probability_diagnostics(
    raw: np.ndarray,
    calibrated: np.ndarray,
    y: np.ndarray,
) -> dict[str, float | int]:
    raw_conf = np.abs(raw - 0.5)
    cal_conf = np.abs(calibrated - 0.5)

    high_raw = (raw >= 0.65) | (raw <= 0.35)
    high_cal = (calibrated >= 0.65) | (calibrated <= 0.35)

    tail_raw = (raw >= 0.80) | (raw <= 0.20)
    tail_cal = (calibrated >= 0.80) | (calibrated <= 0.20)

    raw_pick = raw >= 0.5
    cal_pick = calibrated >= 0.5

    result: dict[str, float | int] = {
        "games": len(raw),
        "mean_raw_confidence": float(raw_conf.mean()),
        "mean_calibrated_confidence": float(cal_conf.mean()),
        "mean_confidence_delta": float(cal_conf.mean() - raw_conf.mean()),
        "high_confidence_raw_rate": float(high_raw.mean()),
        "high_confidence_calibrated_rate": float(high_cal.mean()),
        "high_confidence_rate_delta": float(high_cal.mean() - high_raw.mean()),
        "tail_raw_rate": float(tail_raw.mean()),
        "tail_calibrated_rate": float(tail_cal.mean()),
        "tail_rate_delta": float(tail_cal.mean() - tail_raw.mean()),
        "winner_flip_rate": float((raw_pick != cal_pick).mean()),
    }

    if high_cal.any():
        result["calibrated_high_confidence_accuracy"] = float(
            np.mean(cal_pick[high_cal] == (y[high_cal] >= 0.5))
        )
    else:
        result["calibrated_high_confidence_accuracy"] = 0.0

    if tail_cal.any():
        result["calibrated_tail_accuracy"] = float(
            np.mean(cal_pick[tail_cal] == (y[tail_cal] >= 0.5))
        )
    else:
        result["calibrated_tail_accuracy"] = 0.0

    return result


def _build_holdout_evaluation(
    module,
    data: dict[int, tuple[np.ndarray, np.ndarray]],
    method: str,
) -> list[dict[str, object]]:
    fitter = module.FITTERS[method]
    folds: list[dict[str, object]] = []

    for holdout in SEASONS:
        train_p = np.concatenate(
            [data[s][0] for s in SEASONS if s != holdout]
        )
        train_y = np.concatenate(
            [data[s][1] for s in SEASONS if s != holdout]
        )
        test_p, test_y = data[holdout]

        calibrator = fitter(train_p, train_y)
        calibrated = calibrator.transform(test_p)

        raw_metrics = module._metrics(test_p, test_y)
        calibrated_metrics = module._metrics(calibrated, test_y)

        folds.append(
            {
                "holdout_season": holdout,
                "parameters": {
                    "intercept": calibrator.intercept,
                    "slope": calibrator.slope,
                },
                "raw": raw_metrics,
                "calibrated": calibrated_metrics,
                "delta": {
                    key: calibrated_metrics[key] - raw_metrics[key]
                    for key in ("accuracy", "brier", "log_loss", "ece")
                },
                "probability_diagnostics": _probability_diagnostics(
                    test_p,
                    calibrated,
                    test_y,
                ),
            }
        )

    return folds


def _weighted_average(
    folds: list[dict[str, object]],
    section: str,
    metric: str,
) -> float:
    total = sum(int(row["raw"]["games"]) for row in folds)

    return sum(
        int(row["raw"]["games"])
        * float(row[section][metric])
        for row in folds
    ) / total


def _selection_score(candidate: dict[str, object]) -> float:
    """Lower is better; favor proper scoring rules and calibration."""
    aggregate = candidate["aggregate"]

    return (
        0.45 * float(aggregate["log_loss"])
        + 0.35 * float(aggregate["brier"])
        + 0.20 * float(aggregate["ece"])
    )


def build_report(root: Path) -> dict[str, object]:
    module = _load_88c_module(root)
    previous = _load_88c_report(root)

    failures: list[str] = []
    warnings: list[str] = []

    fingerprint = str(previous["fingerprint_sha256"])
    if fingerprint != EXPECTED_FINGERPRINT:
        failures.append(
            "Step 88C fingerprint does not match the locked six-weight model."
        )

    data, artifacts = module._load_seasons(root)

    candidates: dict[str, object] = {}

    for method in CANDIDATES:
        folds = _build_holdout_evaluation(
            module,
            data,
            method,
        )

        aggregate = {
            metric: _weighted_average(
                folds,
                "calibrated",
                metric,
            )
            for metric in ("accuracy", "brier", "log_loss", "ece")
        }

        raw_aggregate = {
            metric: _weighted_average(
                folds,
                "raw",
                metric,
            )
            for metric in ("accuracy", "brier", "log_loss", "ece")
        }

        delta = {
            metric: aggregate[metric] - raw_aggregate[metric]
            for metric in aggregate
        }

        parameter_stats = _parameter_stats(folds)

        pooled_prob_diag = {
            "mean_confidence_delta": _weighted_average(
                folds,
                "probability_diagnostics",
                "mean_confidence_delta",
            ),
            "high_confidence_rate_delta": _weighted_average(
                folds,
                "probability_diagnostics",
                "high_confidence_rate_delta",
            ),
            "tail_rate_delta": _weighted_average(
                folds,
                "probability_diagnostics",
                "tail_rate_delta",
            ),
            "winner_flip_rate": _weighted_average(
                folds,
                "probability_diagnostics",
                "winner_flip_rate",
            ),
        }

        brier_wins = sum(
            float(row["delta"]["brier"]) < 0.0
            for row in folds
        )
        logloss_wins = sum(
            float(row["delta"]["log_loss"]) < 0.0
            for row in folds
        )
        ece_wins = sum(
            float(row["delta"]["ece"]) < 0.0
            for row in folds
        )

        max_accuracy_damage = min(
            float(row["delta"]["accuracy"])
            for row in folds
        )

        if method == "temperature":
            parameter_stable = (
                parameter_stats["slope_range"] <= 0.75
                and parameter_stats["intercept_range"] == 0.0
            )
        else:
            parameter_stable = (
                parameter_stats["slope_range"] <= 1.0
                and parameter_stats["intercept_range"] <= 0.75
            )

        robust = (
            delta["brier"] < 0.0
            and delta["log_loss"] < 0.0
            and delta["ece"] < 0.0
            and brier_wins >= 3
            and logloss_wins >= 3
            and ece_wins >= 3
            and max_accuracy_damage >= -0.01
            and parameter_stable
        )

        candidate = {
            "folds": folds,
            "aggregate_raw": raw_aggregate,
            "aggregate": aggregate,
            "aggregate_delta": delta,
            "parameter_stats": parameter_stats,
            "probability_diagnostics": pooled_prob_diag,
            "season_brier_wins": brier_wins,
            "season_logloss_wins": logloss_wins,
            "season_ece_wins": ece_wins,
            "worst_season_accuracy_delta": max_accuracy_damage,
            "parameter_stable": parameter_stable,
            "robustness_gate": robust,
        }
        candidate["selection_score"] = _selection_score(candidate)
        candidates[method] = candidate

    ranking = sorted(
        CANDIDATES,
        key=lambda name: float(candidates[name]["selection_score"]),
    )

    robust_candidates = [
        name
        for name in ranking
        if bool(candidates[name]["robustness_gate"])
    ]

    if robust_candidates:
        selected = robust_candidates[0]
        selection_status = "SELECT"
    else:
        selected = None
        selection_status = "REJECT_ALL"

    if selected == "logistic":
        temperature = candidates["temperature"]
        logistic = candidates["logistic"]

        logloss_gain = (
            float(temperature["aggregate"]["log_loss"])
            - float(logistic["aggregate"]["log_loss"])
        )
        brier_gain = (
            float(temperature["aggregate"]["brier"])
            - float(logistic["aggregate"]["brier"])
        )

        # Prefer temperature when logistic's scoring advantage is tiny because
        # temperature cannot move the 0.5 decision boundary.
        if (
            bool(temperature["robustness_gate"])
            and logloss_gain < 0.0015
            and brier_gain < 0.0010
        ):
            selected = "temperature"
            selection_status = "SELECT"

    return {
        "step": "88D",
        "status": "PASS" if not failures else "FAIL",
        "fingerprint_sha256": fingerprint,
        "artifacts": artifacts,
        "candidate_ranking": ranking,
        "selected_method": selected,
        "selection_review": selection_status,
        "candidates": candidates,
        "failures": failures,
        "warnings": warnings,
        "selection_policy": {
            "minimum_brier_wins": 3,
            "minimum_logloss_wins": 3,
            "minimum_ece_wins": 3,
            "worst_accuracy_delta_floor": -0.01,
            "temperature_slope_range_max": 0.75,
            "logistic_slope_range_max": 1.0,
            "logistic_intercept_range_max": 0.75,
            "simplicity_tiebreak": (
                "Prefer temperature when both pass and logistic improves "
                "pooled log loss by <0.0015 and Brier by <0.0010."
            ),
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 88D â€” Calibration Robustness and Selection",
        "",
        f"Fingerprint: `{report['fingerprint_sha256']}`",
        "",
        (
            "Temperature scaling and logistic recalibration are compared using "
            "the same leave-one-season-out population used in Step 88C."
        ),
        "",
        (
            "| Method | Acc Î” | Brier Î” | LogLoss Î” | ECE Î” | "
            "Brier wins | LogLoss wins | ECE wins | Params stable | Gate |"
        ),
        (
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "--- | --- |"
        ),
    ]

    for method in report["candidate_ranking"]:
        row = report["candidates"][method]
        delta = row["aggregate_delta"]

        lines.append(
            f"| {method} | {delta['accuracy']:+.4f} | "
            f"{delta['brier']:+.6f} | {delta['log_loss']:+.6f} | "
            f"{delta['ece']:+.6f} | {row['season_brier_wins']}/4 | "
            f"{row['season_logloss_wins']}/4 | "
            f"{row['season_ece_wins']}/4 | "
            f"{'yes' if row['parameter_stable'] else 'no'} | "
            f"{'PASS' if row['robustness_gate'] else 'REJECT'} |"
        )

    lines.extend(
        [
            "",
            "## Selection",
            "",
            f"- Review: **{report['selection_review']}**",
            (
                "- Selected method: "
                + (
                    f"**{report['selected_method']}**"
                    if report["selected_method"]
                    else "**none**"
                )
            ),
            "",
            (
                "A selected method is ready for a production-contract step; "
                "88D itself does not modify prediction probabilities."
            ),
        ]
    )

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

    report = build_report(args.project_root.resolve())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = (
        args.output_dir
        / "step88d_calibration_robustness_selection.json"
    )
    md_path = (
        args.output_dir
        / "step88d_calibration_robustness_selection.md"
    )

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("=" * 112)
    print("PROJECT GRIDIRON â€” STEP 88D CALIBRATION ROBUSTNESS + SELECTION")
    print("=" * 112)
    print(f"Fingerprint............... {report['fingerprint_sha256']}")
    print("-" * 112)
    print(
        "Method        AccDelta   BrierDelta  LogLossDelta  ECEDelta   "
        "BrierW  LogLossW  ECEW  Params  Gate"
    )
    print("-" * 112)

    for method in report["candidate_ranking"]:
        row = report["candidates"][method]
        delta = row["aggregate_delta"]

        print(
            f"{method:<12} "
            f"{delta['accuracy']:+.4f}     "
            f"{delta['brier']:+.6f}   "
            f"{delta['log_loss']:+.6f}     "
            f"{delta['ece']:+.6f}   "
            f"{row['season_brier_wins']}/4     "
            f"{row['season_logloss_wins']}/4       "
            f"{row['season_ece_wins']}/4   "
            f"{'YES' if row['parameter_stable'] else 'NO ':<6} "
            f"{'PASS' if row['robustness_gate'] else 'REJECT'}"
        )

    print("-" * 112)
    print(f"Selection review.......... {report['selection_review']}")
    print(
        "Selected method.......... "
        f"{report['selected_method'] or 'NONE'}"
    )
    print(f"STATUS: {report['status']}")

    for warning in report["warnings"]:
        print(f"WARN: {warning}")

    for failure in report["failures"]:
        print(f"FAIL: {failure}")

    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 112)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

