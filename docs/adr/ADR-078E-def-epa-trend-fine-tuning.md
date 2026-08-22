# ADR-078E — Defensive EPA Trend Fine-Tuning

## Decision

Step 78D's best aggregate candidate was `def_epa_trend_040`:

- aggregate score: 0.4662
- baseline: 0.4668
- delta: -0.0006
- season record: 2-2
- mean accuracy delta: -0.2%
- 95% CI: [-0.0018, 0.0005]

This is not sufficient for promotion. However, the defensive EPA trend family
improved as the broad-search weight increased through the tested 4.0 boundary.

78E therefore isolates that family and searches 1.5 through 8.0, retaining
4.0 and the zero-feature baseline. No signal combination is attempted.

## Gate

A later provisional lock is justified only if fine tuning identifies a stable
interior optimum with a meaningful score advantage and acceptable accuracy.
If the best result remains at 8.0, extend the boundary before locking.
