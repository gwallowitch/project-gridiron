# Step 88D â€” Calibration Robustness and Selection

Fingerprint: `b12a0d4180ef30298fedcc2a9a676fef6a68589b9434283c1d111fd718427977`

Temperature scaling and logistic recalibration are compared using the same leave-one-season-out population used in Step 88C.

| Method | Acc Î” | Brier Î” | LogLoss Î” | ECE Î” | Brier wins | LogLoss wins | ECE wins | Params stable | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| temperature | +0.0000 | -0.005786 | -0.016002 | -0.038354 | 4/4 | 4/4 | 4/4 | yes | PASS |
| logistic | -0.0018 | -0.006113 | -0.016862 | -0.035162 | 3/4 | 4/4 | 4/4 | yes | REJECT |

## Selection

- Review: **SELECT**
- Selected method: **temperature**

A selected method is ready for a production-contract step; 88D itself does not modify prediction probabilities.
