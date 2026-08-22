# ADR-072: Turnover-Stability Historical Validation

## Status
Accepted.

## Context
77A created leakage-safe turnover-stability artifacts that deliberately split
more repeatable interception/turnover behavior from noisier fumble-recovery
outcomes.

## Decision
77B validates 2022–2025 artifacts for:

- artifact existence;
- unique game rows;
- season integrity;
- home/away known-history coverage;
- non-null feature coverage;
- non-zero feature dispersion;
- prior-history depth;
- offensive/defensive turnover-eligible play sample depth;
- offensive/defensive fumble sample depth.

Coverage gates differ by signal type:

- skill-oriented turnover/interception features >= 85%;
- fumble-recovery/luck features >= 65%;
- home/away known coverage >= 90%.

Sample-depth gates:

- prior history >= 5 weeks on average;
- turnover-eligible plays >= 150 on average;
- fumbles/opponent fumbles >= 4 on average.

The looser fumble coverage threshold is intentional because many team-week
histories legitimately contain no fumbles. This is a data-quality gate, not a
predictive-value judgment.

## Scope
77B does not alter experiment weights, runtime scoring, or
`config/experiments.toml`.

If green, 77C may add experiment configuration support.
