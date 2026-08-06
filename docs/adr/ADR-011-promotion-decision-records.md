# ADR-011: Promotion Decision Records

## Status

Accepted

## Decision

Create a promotion-decision layer above statistical validation. Candidates are ranked by promotion status, paired mean score delta, winner-accuracy delta, and name. A candidate is recommended only when its status is `PASS`. Recommendations never change production automatically.

Each review writes `promotion_decision.json` and appends to `promotion_history.json`.
