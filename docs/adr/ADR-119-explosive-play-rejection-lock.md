# ADR-119 — Explosive-Play Rejection Lock

## Decision

Reject and park the Step 86 explosive-play family.

## Evidence

Step 86C tested twelve isolated candidates:

- explosive pass-rate advantage;
- explosive rush-rate advantage;
- overall explosive-play-rate advantage.

The locked six-weight baseline won every research season and ranked first in
the cross-season aggregate.

The least-bad candidate, `explosive_rush_025`, still produced:

- season record: 0-4;
- mean score delta: +0.0001;
- confidence interval: [0.0000, 0.0003];
- mean accuracy delta: -0.1%;
- promotion status: REJECT.

Every tested candidate had a positive aggregate delta versus baseline.

## Consequence

No Step 86 feature is promoted.

The active model remains the six-weight lock:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.0
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

Step 87 should test one final differentiated feature family before the project
pivots from feature discovery into combined-model, calibration, and market
work.
