# ADR-149: Step 91H Prospective Integrity Closure

## Status

Accepted.

## Decision

Freeze a prospective-only operational integrity protocol around the unchanged Step
91C-91G system. Every scheduled game enters a hash-chained manifest; every capture
attempt retains raw bytes, SHA256, local receipt time, provider times, status, and
reason. Accepted evidence remains delegated to the frozen decision ledger.

The capture window, uniform freshness limit, source hierarchy, settlement deadline,
outcome-blind edge tie ordering, balanced-market bounds, complete-season rule, and
probability-metric population are frozen before evidence. They are operational
assumptions, not historical findings or model improvements.

## Consequences

Silent omission, selective timing, stale input, unretained rejection, ledger mutation,
selective settlement delay, and ambiguous robustness populations become detectable.
The local clock and offline chain retain explicitly documented limits; neither is
misrepresented as external cryptographic publication. Any later methodological change
requires a new protocol/candidate identity and cannot rewrite prior evidence.
