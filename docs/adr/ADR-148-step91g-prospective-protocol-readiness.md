# ADR-148: Step 91G Prospective Protocol Readiness

## Status

Accepted.

## Context

Step 91F can accumulate real prospective evidence, but Step 91E/F reported missing
edge-tail definitions. Before first collection, repository-local history and the live
Step 91C-91F chain must be audited without changing the candidate.

## Decision

Classify the system as `READY_WITH_DOCUMENTED_LIMITATION`. Published history recovers
ranked exclusions of the largest 1%, 5%, and 10% positive edges. A local Git object
also recovers descending sort plus floor-count removal. However, that executable source
is not a published frozen Step 91B artifact and equal-edge ties are only implicitly
ordered. This does not block untouched evidence capture, but it blocks an unconditional
`READY` classification and any future promotion declaration until resolved.

The Step 91G implementation is read-only. It verifies frozen constants/configuration,
discovers the Step 91C-91F chain, reports empty real-evidence state, and documents exact
operator inputs and commands. It does not modify Step 91C-91F, ingest observations,
settle games, tune parameters, infer trims from results, or fabricate evidence.

## Consequences

Operators may begin genuine pre-kickoff 2026 collection under the frozen candidate.
All incomplete, late, duplicate, or unavailable inputs follow fail-closed rules. The
promotion gate retains an explicit provenance/tie limitation rather than a guessed
methodology.
