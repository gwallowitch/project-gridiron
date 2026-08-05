# ADR-007: Prediction Experiment Framework

## Status
Accepted

## Context
Prediction Engine v1 established a measurable historical baseline, but changing
production constants by hand would make experiments difficult to reproduce and
compare.

## Decision
Introduce a configuration-driven experiment subsystem that generates temporary
predictions, evaluates them with the existing backtester, ranks results with a
published multi-metric score, and appends results to a JSON registry.

The production prediction defaults remain unchanged in v0.8.0a.

## Consequences
- Experiments are reproducible and version controlled.
- Model promotion is separated from research.
- The initial selection score is explicit but remains a policy choice that may
  evolve after more seasons are available.
