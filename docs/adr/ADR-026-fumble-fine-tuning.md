# ADR-026: Lost-Fumble Fine-Tuning

## Status
Accepted for research.

## Context
Milestone 65D tested interceptions and lost fumbles independently.

Interception weighting clearly deteriorated the model across every tested value:
all interception candidates went 0-4 by season, and higher weights produced
progressively worse aggregate scores. Interception weighting is therefore fixed
at zero for the remainder of the v1.0 turnover study.

Lost fumbles showed a small but more promising signal. The 65D aggregate leader
was `turnover_fumble_025`, with:
- a 3-1 season record,
- a small negative score delta versus baseline,
- a small positive accuracy delta,
- but a confidence interval that still crossed zero.

## Decision
65E fine-tunes only the low lost-fumble weight region:

- 0.00 baseline
- 0.10
- 0.15
- 0.20
- 0.25
- 0.30
- 0.35
- 0.40
- 0.50

Interception weight remains 0.00.

## Foundation
This remains an isolated turnover study:
- rest = 0.20
- QB = 0.00
- injury = 0.00
- early-down offense = 0.00
- early-down defense = 0.00
- early-down success = 0.00
- turnover interceptions = 0.00

## Season scope
Use the modern profile: 2022-2025.

## Interpretation
65E is the final turnover-weight refinement for v1.0.

65F will make the keep/reject decision. If the fumble signal remains weak,
unstable, or statistically inconclusive, production turnover weights should both
remain zero and the feature family should be archived for later research.

No production model setting changes in 65E.
