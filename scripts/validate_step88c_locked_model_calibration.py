"""Step 88C — leakage-safe locked-model calibration research."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

EXPECTED_FINGERPRINT = (
    "b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977"
)
SEASONS = (2022, 2023, 2024, 2025)


def _load_88b_module(root: Path):
    path = root / "scripts" / "validate_step88b_combined_model_diagnostics.py"
    if not path.exists():
        raise FileNotFoundError(
            "Step 88B validator is required so 88C evaluates the exact same "
            f"game-level population: {path}"
        )
    spec = importlib.util.spec_from_file_location("_step88b_for_88c", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    return np.log(p / (1.0 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x))


def _log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-15, 1.0 - 1e-15)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _accuracy(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p >= 0.5) == (y >= 0.5)))


def _ece(p: np.ndarray, y: np.ndarray) -> float:
    total = len(p)
    if total == 0:
        return 0.0
    value = 0.0
    for i in range(10):
        lo = i / 10.0
        hi = (i + 1) / 10.0
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        count = int(mask.sum())
        if count:
            value += count * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return value / total


def _metrics(p: np.ndarray, y: np.ndarray) -> dict[str, float | int]:
    return {
        "games": len(p),
        "accuracy": _accuracy(p, y),
        "brier": _brier(p, y),
        "log_loss": _log_loss(p, y),
        "ece": _ece(p, y),
    }


@dataclass(frozen=True)
class Calibrator:
    name: str
    intercept: float
    slope: float

    def transform(self, p: np.ndarray) -> np.ndarray:
        return _sigmoid(self.intercept + self.slope * _logit(p))


def _fit_intercept_only(p: np.ndarray, y: np.ndarray) -> Calibrator:
    z = _logit(p)
    best = (float("inf"), 0.0)
    for intercept in np.linspace(-1.5, 1.5, 1201):
        loss = _log_loss(_sigmoid(z + intercept), y)
        if loss < best[0]:
            best = (loss, float(intercept))
    return Calibrator("intercept_only", best[1], 1.0)


def _fit_temperature(p: np.ndarray, y: np.ndarray) -> Calibrator:
    z = _logit(p)
    best = (float("inf"), 1.0)
    for slope in np.linspace(0.25, 2.5, 901):
        loss = _log_loss(_sigmoid(slope * z), y)
        if loss < best[0]:
            best = (loss, float(slope))
    return Calibrator("temperature", 0.0, best[1])


def _fit_logistic(p: np.ndarray, y: np.ndarray) -> Calibrator:
    z = _logit(p)
    intercept = 0.0
    slope = 1.0

    # Newton/IRLS for a two-parameter logistic recalibration.
    for _ in range(100):
        eta = intercept + slope * z
        q = _sigmoid(eta)
        w = np.maximum(q * (1.0 - q), 1e-8)
        x0 = np.ones_like(z)
        g0 = float(np.sum(y - q))
        g1 = float(np.sum((y - q) * z))
        h00 = float(np.sum(w * x0 * x0))
        h01 = float(np.sum(w * z))
        h11 = float(np.sum(w * z * z))
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        d0 = (h11 * g0 - h01 * g1) / det
        d1 = (-h01 * g0 + h00 * g1) / det
        intercept += d0
        slope += d1
        if max(abs(d0), abs(d1)) < 1e-10:
            break

    slope = max(0.05, min(4.0, slope))
    intercept = max(-3.0, min(3.0, intercept))
    return Calibrator("logistic", float(intercept), float(slope))


FITTERS = {
    "intercept_only": _fit_intercept_only,
    "temperature": _fit_temperature,
    "logistic": _fit_logistic,
}


def _load_seasons(root: Path) -> tuple[dict[int, tuple[np.ndarray, np.ndarray]], dict[int, str]]:
    m88b = _load_88b_module(root)
    paths = m88b.ProjectPaths.from_root(root)

    data: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    artifacts: dict[int, str] = {}

    for season in SEASONS:
        schedule = pl.read_parquet(paths.schedule_file(season))
        raw, artifact = m88b._load_game_level(paths, season)
        frame = m88b._normalize_game_frame(raw, schedule)
        p = np.asarray(frame["model_home_win_probability"].to_list(), dtype=float)
        y = np.asarray(frame["actual_home_win"].to_list(), dtype=float)
        data[season] = (p, y)
        artifacts[season] = str(artifact)

    return data, artifacts


def _fingerprint(root: Path) -> str:
    path = root / "data" / "reports" / "research" / "step88a_locked_model_integrity.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload["model"]["fingerprint_sha256"])


def _aggregate_fold_metrics(folds: list[dict[str, object]], key: str) -> dict[str, float]:
    total = sum(int(f["raw"]["games"]) for f in folds)
    names = ("accuracy", "brier", "log_loss", "ece")
    result: dict[str, float] = {}
    for name in names:
        result[name] = sum(
            int(f["raw"]["games"]) * float(f[key][name])
            for f in folds
        ) / total
    return result


def build_report(root: Path) -> dict[str, object]:
    fingerprint = _fingerprint(root)
    failures: list[str] = []
    if fingerprint != EXPECTED_FINGERPRINT:
        failures.append("Locked-model fingerprint differs from Step 88A.")

    data, artifacts = _load_seasons(root)
    methods: dict[str, object] = {}

    for method, fitter in FITTERS.items():
        folds: list[dict[str, object]] = []
        for holdout in SEASONS:
            train_p = np.concatenate([data[s][0] for s in SEASONS if s != holdout])
            train_y = np.concatenate([data[s][1] for s in SEASONS if s != holdout])
            test_p, test_y = data[holdout]

            calibrator = fitter(train_p, train_y)
            calibrated = calibrator.transform(test_p)

            raw = _metrics(test_p, test_y)
            cal = _metrics(calibrated, test_y)
            folds.append(
                {
                    "holdout_season": holdout,
                    "train_seasons": [s for s in SEASONS if s != holdout],
                    "parameters": {
                        "intercept": calibrator.intercept,
                        "slope": calibrator.slope,
                    },
                    "raw": raw,
                    "calibrated": cal,
                    "delta": {
                        "accuracy": cal["accuracy"] - raw["accuracy"],
                        "brier": cal["brier"] - raw["brier"],
                        "log_loss": cal["log_loss"] - raw["log_loss"],
                        "ece": cal["ece"] - raw["ece"],
                    },
                }
            )

        raw_agg = _aggregate_fold_metrics(folds, "raw")
        cal_agg = _aggregate_fold_metrics(folds, "calibrated")
        deltas = {k: cal_agg[k] - raw_agg[k] for k in raw_agg}
        season_brier_wins = sum(float(f["delta"]["brier"]) < 0.0 for f in folds)
        season_logloss_wins = sum(float(f["delta"]["log_loss"]) < 0.0 for f in folds)
        season_ece_wins = sum(float(f["delta"]["ece"]) < 0.0 for f in folds)

        # Conservative research gate: calibration must improve both proper
        # scoring rules pooled, improve ECE, avoid >0.5pp accuracy damage,
        # and improve Brier/log loss in at least 3/4 held-out seasons.
        candidate = (
            deltas["brier"] < 0.0
            and deltas["log_loss"] < 0.0
            and deltas["ece"] < 0.0
            and deltas["accuracy"] >= -0.005
            and season_brier_wins >= 3
            and season_logloss_wins >= 3
        )

        methods[method] = {
            "folds": folds,
            "aggregate_raw": raw_agg,
            "aggregate_calibrated": cal_agg,
            "aggregate_delta": deltas,
            "season_brier_wins": season_brier_wins,
            "season_logloss_wins": season_logloss_wins,
            "season_ece_wins": season_ece_wins,
            "passes_candidate_gate": candidate,
        }

    ranking = sorted(
        methods,
        key=lambda name: (
            float(methods[name]["aggregate_calibrated"]["log_loss"]),
            float(methods[name]["aggregate_calibrated"]["brier"]),
            float(methods[name]["aggregate_calibrated"]["ece"]),
        ),
    )
    best = ranking[0]
    promotion = (
        "CANDIDATE"
        if methods[best]["passes_candidate_gate"]
        else "REJECT"
    )

    return {
        "step": "88C",
        "status": "PASS" if not failures else "FAIL",
        "fingerprint_sha256": fingerprint,
        "artifacts": artifacts,
        "method_ranking": ranking,
        "best_method": best,
        "promotion_review": promotion,
        "methods": methods,
        "failures": failures,
        "notes": [
            "All calibration evaluation is leave-one-season-out.",
            "No feature or model weights are changed.",
            "PASS means the research ran safely; CANDIDATE/REJECT is the calibration decision.",
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Step 88C — Locked-Model Calibration Research",
        "",
        f"Fingerprint: `{report['fingerprint_sha256']}`",
        "",
        "All results use leave-one-season-out calibration fitting.",
        "",
        "| Method | Acc Δ | Brier Δ | LogLoss Δ | ECE Δ | Brier wins | LogLoss wins | Gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name in report["method_ranking"]:
        row = report["methods"][name]
        d = row["aggregate_delta"]
        lines.append(
            f"| {name} | {d['accuracy']:+.4f} | {d['brier']:+.6f} | "
            f"{d['log_loss']:+.6f} | {d['ece']:+.6f} | "
            f"{row['season_brier_wins']}/4 | {row['season_logloss_wins']}/4 | "
            f"{'CANDIDATE' if row['passes_candidate_gate'] else 'REJECT'} |"
        )
    lines += [
        "",
        f"Best method: **{report['best_method']}**",
        f"Promotion review: **{report['promotion_review']}**",
        "",
        "PASS indicates diagnostic integrity, not automatic calibration promotion.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("data/reports/research"))
    args = parser.parse_args()

    report = build_report(args.project_root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "step88c_locked_model_calibration_research.json"
    md_path = args.output_dir / "step88c_locked_model_calibration_research.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print("=" * 108)
    print("PROJECT GRIDIRON — STEP 88C LOCKED-MODEL CALIBRATION RESEARCH")
    print("=" * 108)
    print(f"Fingerprint............... {report['fingerprint_sha256']}")
    print("Validation................ Leave-one-season-out (2022–2025)")
    print("-" * 108)
    print("Method              AccDelta    BrierDelta  LogLossDelta  ECEDelta    BrierW  LogLossW  Gate")
    print("-" * 108)
    for name in report["method_ranking"]:
        row = report["methods"][name]
        d = row["aggregate_delta"]
        gate = "CANDIDATE" if row["passes_candidate_gate"] else "REJECT"
        print(
            f"{name:<19} {d['accuracy']:+.4f}      {d['brier']:+.6f}   "
            f"{d['log_loss']:+.6f}     {d['ece']:+.6f}   "
            f"{row['season_brier_wins']}/4      {row['season_logloss_wins']}/4       {gate}"
        )
    print("-" * 108)
    print(f"Best method............... {report['best_method']}")
    print(f"Promotion review.......... {report['promotion_review']}")
    print(f"STATUS: {report['status']}")
    for failure in report["failures"]:
        print(f"FAIL: {failure}")
    print(f"JSON: {json_path.resolve()}")
    print(f"MD:   {md_path.resolve()}")
    print("=" * 108)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
