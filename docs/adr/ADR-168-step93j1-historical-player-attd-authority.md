# ADR-168: Step 93J.1 historical Player ATTD acquisition authority

## Status

Pending independent review. Execution is disabled.

## Decision

Project Gridiron defines one non-production research authority type:
`HISTORICAL_PLAYER_ATTD_VALIDATION_SAMPLE_V1`. It is bound to the exact frozen
Step 93C manifest SHA-256 and its six historical `player_anytime_td` snapshot
requests. It does not authorize current, live, prospective, recurring, outcome,
modeling, ROI, or wagering activity.

The deterministic authority artifact is
`data/reference/player_td_sample_v1/step93j1_historical_authority.json`. Its
embedded authority SHA-256 is calculated over every other canonical artifact
field. Step 93J.1 does not pin that hash as reviewed authority and cannot call a
provider. The historical entry point is an unconditional fail-closed tombstone.
Step 93J.2 must explicitly pin the independently reviewed hash in source and
undergo separate review before execution can be introduced. A caller-supplied
hash or environment variable is not an activation mechanism.

Any future one-shot state namespace is derived from both the reviewed authority
SHA-256 and frozen manifest SHA-256 and must reuse the Step 93I claim, ledger,
continuity, replay, concurrency, and six-call protections.

## Future raw evidence destination

Future raw responses belong under
`data/research/player_td_validation/step93c_sample/raw/<authority_sha256>/`, not
`data/operational/`. Each item has deterministic response and metadata names
based on its frozen sample-item ID. Metadata must retain the authority,
manifest, sample-item, provider-event, requested-snapshot, acquisition-time,
HTTP-status, non-secret request-scope, byte-count, and raw SHA-256 identities.
Conflicting existing bytes must never be overwritten. No raw provider response
is created in Step 93J.1.

Credentials are outside the artifact, state, metadata, retained URL, and logs.
A future executor may read `GRIDIRON_ODDS_API_KEY` only at execution time and
must not expose its value.

## Limitations

The 60-credit value remains a planning estimate, not a billing guarantee.
Provider event IDs are unresolved in the frozen manifest and require separate
reviewed resolution before any future execution. No outcome data or modeling is
authorized.
