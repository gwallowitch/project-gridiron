# ADR-003: Project Gridiron Rating Version 1

## Status

Accepted

## Context

Project Gridiron now produces leak-free weekly performance ratings and weekly
strength-of-schedule ratings. The platform needs a transparent baseline power
rating before more complex iterative models or predictive calibration are
introduced.

## Decision

PGR v1 is defined as:

```text
PGR = Performance Rating + 0.50 × (Strength of Schedule Rating − 100)
```

The performance rating is the team's cumulative weekly overall rating. The
strength-of-schedule input is produced by the existing leak-free SoS pipeline.
A schedule rating of 100 is neutral and therefore contributes no adjustment.

## Rationale

- The formula is deterministic and directly explainable.
- Schedule strength matters without overwhelming observed performance.
- Week 1 naturally reduces to the performance rating because SoS is neutral.
- The coefficient is explicit and version-controlled.
- PGR v1 creates a baseline that future iterative models must outperform.

## Consequences

- The 0.50 schedule coefficient is provisional and must be evaluated through
  historical backtesting before it is changed.
- PGR v1 is not a calibrated point-spread estimate.
- PGR v1 does not include injuries, home field, rest, travel, or recent-form
  weighting.
- Future mathematical changes require a new model version and ADR.
