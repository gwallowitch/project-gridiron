# ADR-123 — Close Standalone Feature Discovery

## Decision

Reject and park the Step 87 play-consistency family and close the standalone
feature-discovery phase.

## Evidence

Step 87C tested sixteen isolated candidates across:

- offensive success-rate advantage;
- defensive success-prevention advantage;
- combined success-rate matchup advantage;
- negative-play matchup advantage.

The top aggregate candidate was `negative_matchup_025`, but its practical
effect was indistinguishable from zero:

- mean score delta: approximately 0.0000;
- 95% confidence interval: approximately [0.0000, 0.0000];
- season record: 2-2;
- mean accuracy delta: 0.0%;
- promotion status: INCONCLUSIVE.

The remaining candidates were flat to worse, and larger weights generally
degraded performance.

## Consequence

No Step 87 feature is promoted.

The active model remains the six-weight lock:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.0
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

Standalone feature discovery is now closed. The next development phase should
evaluate the locked model as a whole: combined-model integrity, calibration,
walk-forward stability, market comparison, and betting-decision logic.
