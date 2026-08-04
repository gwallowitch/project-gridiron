# ADR-004: Benchmark Framework

## Status

Accepted.

## Context

Project Gridiron now produces weekly PGR values. Future rating changes require an objective baseline so model health is measured rather than judged by appearance.

## Decision

Introduce a standalone benchmark package that evaluates persisted PGR datasets. Version 1 measures distribution and week-to-week stability. It does not claim predictive accuracy because a prediction engine has not yet been implemented.

The benchmark reports league center, spread, standard deviation, and absolute weekly movement. Population standard deviation (`ddof=0`) is used explicitly for deterministic league-level summaries.

## Consequences

- Future PGR changes can be compared against a stable baseline.
- Benchmark output remains descriptive until game-outcome evaluation is added.
- Runtime is reported but excluded from deterministic comparisons.
- Benchmark history can be stored as JSON Lines without changing the core evaluator.
