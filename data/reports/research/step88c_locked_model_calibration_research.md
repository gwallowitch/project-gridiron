# Step 88C — Locked-Model Calibration Research

Fingerprint: `b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977`

All results use leave-one-season-out calibration fitting.

| Method | Acc Δ | Brier Δ | LogLoss Δ | ECE Δ | Brier wins | LogLoss wins | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| logistic | -0.0018 | -0.006113 | -0.016862 | -0.035162 | 3/4 | 4/4 | CANDIDATE |
| temperature | +0.0000 | -0.005786 | -0.016002 | -0.038354 | 4/4 | 4/4 | CANDIDATE |
| intercept_only | +0.0009 | +0.000003 | -0.000039 | -0.003028 | 2/4 | 2/4 | REJECT |

Best method: **logistic**
Promotion review: **CANDIDATE**

PASS indicates diagnostic integrity, not automatic calibration promotion.
