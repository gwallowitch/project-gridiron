# ADR-126 — Leakage-Safe Calibration Research

Step 88B found pooled ECE of 0.0777 and meaningful season-to-season variation.
The six-weight model remains locked.

Step 88C therefore evaluates probability recalibration without changing model
features or weights. Calibration parameters are fitted on three seasons and
evaluated on the fourth, repeated for every 2022–2025 holdout season.

Three deliberately simple methods are evaluated:

1. intercept-only logistic correction;
2. temperature/slope scaling;
3. two-parameter logistic recalibration.

A method is only a promotion candidate when pooled Brier, log loss, and ECE
improve, accuracy damage is no worse than 0.5 percentage points, and both
Brier and log loss improve in at least three of four held-out seasons.

A successful script execution is distinct from a successful calibration
candidate. This prevents the research framework from promoting a transform
merely because it was tested.
