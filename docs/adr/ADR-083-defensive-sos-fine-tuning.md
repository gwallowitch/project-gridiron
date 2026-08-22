# ADR-083: Defensive Schedule Difficulty Fine-Tuning

## Context

Step 79C isolated four opponent-adjusted feature families against the promoted
five-weight baseline.

Only defensive schedule difficulty showed a credible direction of improvement:

- 1.25: score delta -0.0002, season record 3-1, accuracy delta -0.1%
- 2.50: score delta -0.0004, season record 3-1, accuracy delta -0.1%
- 5.00: score delta -0.0005, season record 2-2, accuracy delta -0.4%
- 7.50: score delta -0.0008, season record 2-2, accuracy delta -0.4%, rejected

The broad-search numerical winner therefore was not the preferred research
candidate because the higher weights degraded winner accuracy and season
stability.

## Decision

79D isolates defensive schedule difficulty and tests:

0.00, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.00.

All other opponent-adjusted weights remain zero.

The promoted five-weight baseline is frozen:

- rest = 0.20
- offensive sack = 10.00
- punt return = 0.24
- long-field avoidance = 1.00
- defensive EPA trend = 5.25

## Interpretation

79D should select the best score/accuracy/stability compromise, not simply the
lowest aggregate selection score.

A follow-up robustness step is justified only if the refined region retains
meaningful score improvement without the approximately -0.4 percentage-point
winner-accuracy degradation seen at the high end of the 79C search.
