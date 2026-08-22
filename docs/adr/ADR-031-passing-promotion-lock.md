# ADR-031: Passing Promotion Lock

## Status
Accepted for v1.0.

## Context
Milestones 66D and 66E evaluated six passing feature families across the
2022-2025 modern research window.

The broad and fine-tuned studies showed that offensive sack-rate advantage was
the only passing feature family with sufficiently strong and stable evidence to
retain for v1.0.

The aggregate score leader was `off_sack_weight = 20.0`, but its paired 95%
confidence interval still crossed zero and its season record was 3-1.

The nearby `off_sack_weight = 10.0` candidate produced:
- 4-0 season record;
- mean score delta of approximately -0.0009;
- 95% confidence interval approximately [-0.0018, -0.0002];
- mean accuracy delta of approximately +0.5%.

## Decision
Project Gridiron v1.0 selects:

`off_sack_weight = 10.0`

All other passing feature weights remain zero.

## Robustness override
The research framework is explicitly allowed to prefer a nearby candidate over
the raw aggregate-score leader when the nearby candidate provides materially
better cross-season stability and stronger paired statistical evidence.

For 66F, robustness overrides the larger aggregate improvement at weight 20.

## Rejected / archived passing families
- offensive pass EPA;
- defensive pass EPA;
- passing success rate;
- defensive sack-rate advantage;
- explosive-pass rate.

These features remain available for later research but are excluded from the
v1.0 promoted configuration.

## Production boundary
66F records the selected research configuration. Any separate production-model
configuration or deployment path must consume this value explicitly; this ADR
does not silently mutate unrelated production behavior.
