# ADR-076: Recent-Form Historical Validation

## Status
Accepted as the Step 78B validation gate.

## Context
78A introduced leakage-safe recent-form and trend features based on prior-week
history. Before wiring those features into the experiment engine, Project
Gridiron needs evidence that they are broadly available and non-degenerate
across the research seasons.

## Decision
78B validates the persisted 2022–2025 recent-form artifacts without changing
model scoring or the experiment grid.

The gate checks:
- unique game rows;
- adequate schedule volume;
- week-3-and-later availability for both teams;
- overall feature coverage;
- non-zero feature dispersion;
- non-trivial non-zero observation rates.

## Gate thresholds
- at least 250 rows per research season;
- at least 90% both-team recent-form availability from week 3 onward;
- at least 75% total coverage for each candidate feature;
- positive numerical dispersion;
- at least 50% non-zero observations.

## Interpretation
A PASS means the recent-form family is technically suitable for controlled
research. It is not evidence of predictive lift and does not promote any
feature.

## Next step
78C should wire a small, isolated experiment surface for the validated trend
families while retaining the existing locked field-position improvement.
