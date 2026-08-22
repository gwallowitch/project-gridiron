# ADR-117 — Explosive-Play Historical Validation

Step 86A materialized four research seasons with approximately 94.4% coverage
for explosive pass, rush, and overall rate advantages.

Step 86B validates the family before any model weights are introduced.

The gate checks:

- one row per game;
- season integrity;
- Week 1 unknown behavior;
- Week 2+ prior-history availability;
- feature coverage above 90%;
- non-zero dispersion;
- finite numeric values;
- underlying rate bounds within [0, 1];
- explicit no-current-game leakage.

A PASS permits Step 86C isolated experiment wiring. It does not imply
predictive value.
