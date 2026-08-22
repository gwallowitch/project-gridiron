# ADR-062: Long-Field Avoidance Fine Tuning

## Status
Accepted for focused research.

## Why 74E exists
74D produced the first credible field-position signal:

- `field_long_avoid_100` ranked first overall;
- cross-season mean selection-score delta: `-0.0004`;
- season record: `4-0-0`;
- 95% CI: `[-0.0008, -0.0001]`;
- mean accuracy delta: `+0.3%`.

The promotion review remained INCONCLUSIVE only because the gain did not clear
the project's practical-improvement threshold.

## Decision
Fine-tune the long-field avoidance weight around and below the broad-search
winner. The broad grid began at 1.0, so 74E explicitly tests smaller weights to
determine whether the true optimum sits below that boundary.

Weights:
- 0.10
- 0.25
- 0.50
- 0.75
- 1.00
- 1.25
- 1.50
- 1.75

The baseline remains:
- rest 0.20
- offensive sack 10.0
- punt return 0.24
- long-field avoidance 0.0

No other field-position component is active.
