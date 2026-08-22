# ADR-083 — Opponent-Adjusted Experiment Wiring

## Decision

Wire the four leakage-safe Step 79A opponent-adjusted signals into the common
experiment and research runners, but test them one family at a time against the
promoted five-weight baseline.

The 79C search contains four magnitudes (1.25, 2.50, 5.00, 7.50) for each of:

- opponent-adjusted offensive EPA difference;
- opponent-adjusted defensive EPA difference;
- offensive schedule-difficulty advantage;
- defensive schedule-difficulty advantage.

## Guardrails

The existing five promoted weights remain fixed. Missing opponent-adjusted
values are neutralized to zero after the feature join. Any non-zero 79C weight
requires the validated opponent-adjusted artifact and expected schema.

79C is a screening step, not a promotion step. A promising family must survive
subsequent fine-tuning and robustness validation before promotion.
