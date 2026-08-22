# ADR-127 — Calibration Robustness and Selection

## Context

Step 88C produced two credible calibration candidates.

Temperature scaling:
- Brier delta: -0.005786;
- log-loss delta: -0.016002;
- ECE delta: -0.038354;
- accuracy delta: 0.0000;
- Brier/log-loss wins: 4/4.

Logistic recalibration:
- Brier delta: -0.006113;
- log-loss delta: -0.016862;
- ECE delta: -0.035162;
- accuracy delta: -0.0018;
- Brier wins: 3/4;
- log-loss wins: 4/4.

## Decision

Step 88D performs a head-to-head leave-one-season-out robustness review.

It examines:

- season-by-season Brier, log loss, and ECE wins;
- worst held-out-season accuracy damage;
- calibration parameter stability;
- confidence compression/expansion;
- high-confidence population changes;
- extreme probability tail changes;
- winner-pick flip rate.

The selection gate requires proper-score and ECE improvement in at least three
of four seasons, acceptable worst-season accuracy damage, and stable
calibration parameters.

When both methods pass, simplicity is used as a tie-break. Temperature scaling
is preferred if logistic's pooled proper-score advantage is very small,
because temperature scaling cannot move the 0.5 winner-decision boundary.

## Consequence

Step 88D selects a calibration method but does not modify production
probability logic. A selected candidate proceeds to the next contract and
implementation step.
