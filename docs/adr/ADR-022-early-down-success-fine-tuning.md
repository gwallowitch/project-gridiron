# ADR-022: Early-Down Success-Rate Fine-Tuning

## Status
Accepted for research.

## Context
64D showed that offensive EPA and defensive EPA deteriorated with increasing
weights, while early-down success rate was the only family that improved the
aggregate research score.

The broad-grid leader was `early_success_150`, with `early_success_200` also
winning two individual seasons.

## Decision
64E fine-tunes only the success-rate signal at:

0, 8, 10, 12, 14, 15, 16, 18, 20, 22

Other early-down weights remain zero.

## Foundation
- rest = 0.20
- QB = 0.00
- injury = 0.00

This remains an isolated feature study. Combined-feature interactions are
deferred until the later combined-feature phase.

## Season scope
Use the modern profile: 2022-2025.

## Interpretation
64E identifies the best local success-rate weight. 64F makes the keep/reject
decision based on aggregate score, season consistency, confidence interval,
accuracy delta, and practical significance.

No production model setting changes in 64E.
