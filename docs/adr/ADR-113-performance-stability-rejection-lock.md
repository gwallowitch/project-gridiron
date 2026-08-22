# ADR-113 — Performance Stability Rejection Lock

## Decision

Reject and park the Step 84 performance-stability family.

## Evidence

Step 84C tested 12 candidates across three isolated feature families:

- performance stability;
- recent margin;
- close-game experience.

The locked six-weight baseline ranked first in the cross-season aggregate.

The least-bad candidate, `stability_005`, still produced:

- positive mean score delta: +0.0001;
- season record: 1-3;
- mean accuracy delta: -0.1%;
- promotion status: REJECT.

Other weights generally degraded further as magnitude increased.

## Consequence

No Step 84 weight is promoted.

The active model remains the six-weight lock:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.0
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

Step 85 should explore a different feature family rather than continue tuning
performance-stability signals.
