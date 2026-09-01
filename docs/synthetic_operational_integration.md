# Synthetic Operational Integration Contract

## Status and boundary

This unnumbered, post-Step 91O contract is a local readiness artifact. It does
not activate Core-Three, authenticate an external claim, authorize collection,
or create prospective evidence. It performs no filesystem, network, database,
provider, credential, manifest, ledger, or wagering operation.

The contract composes, in memory:

`ScheduleVersion -> AcquisitionEnvelope -> AtomicObservation -> Core-Three
consensus -> frozen candidate inputs -> DraftKings offered-price decision ->
synthetic validation result -> attempt lifecycle`

The original seven-book protocol and the Core-Three protocol remain distinct.
The integration uses `build_consensus_preview` for exactly BetMGM, FanDuel, and
DraftKings. It does not call or relabel the original seven-book consensus.

## Frozen scientific contract

The integration validates these values exactly and rejects any drift:

- candidate: `market-plus-def-epa-capped-0425-v1`
- variant: `market-plus-def-epa-capped-0425-core-three-v1`
- market coefficient: `4.980172`
- DEF EPA coefficient: `1.044827`
- intercept: `-2.514766`
- residual cap: `0.0425`
- eligibility: strictly positive edge
- offered-price venue: DraftKings
- population: 2026 regular season, weeks 1 through 16

The Core-Three consensus is the mean of each required book's two-way,
no-vig home probability. The frozen logistic candidate is evaluated from that
consensus and the explicitly versioned DEF EPA input; its residual is capped at
plus or minus 4.25 percentage points around consensus. The selected side is the
direction of the candidate residual (home when the residual is zero). Its edge
is candidate side probability minus the break-even probability of the same
response's DraftKings offered price. Only `edge > 0` produces
`POSITIVE_EDGE_CANDIDATE`; zero and negative edges produce `NO_BET`.

Neither result is operationally eligible. Every result exposes the following
immutable properties as `False`:

- `real_evidence_write_allowed`
- `external_claims_authenticated`
- `activation_allowed`
- `prospective_evidence`

## Missingness and rejection

DEF EPA must have a synthetic source and vintage. `OBSERVED` requires a finite
float. The only permitted missing value is an explicit `WEEK_ONE_NEUTRAL` state
in week 1, which maps to zero. All other missing or malformed inputs reject.

The fixed validation order is published by `VALIDATION_ORDER`. A valid
transaction creates an immutable decision record with a structural transaction
binding and replay identity. A contract failure creates a `REJECTED` result
with no decision record. Rejection never falls through to a default bet or
write path. Unexpected numeric, type, and arithmetic failures are normalized to
a non-sensitive `INVALID_INTEGRATION_INPUT` rejection.

## Identity and replay rules

Game, provider-event, response, response digest, receipt time, kickoff time,
schedule version, acquisition attempt, request, DraftKings prices, approval,
validation, and authority subjects must agree across their originating
contracts. Every synthetic authority artifact is additionally bound to the
complete non-authority transaction context, including the normalized market
contents and attempt history. The decision record recomputes its mathematics
and bindings during construction, so caller-supplied or altered decisions are
rejected.

The provider-response SHA-256 remains a supplied, non-authenticated content
identity. Because raw response bytes are intentionally not retained, this layer
cannot independently reconstruct that raw digest. Instead, it binds the digest
and the fully revalidated normalized contents together in the authority context.
Regenerating fixture authorities creates a new synthetic context; it never
authenticates the provider or proves the raw-to-normalized transformation.

Attempt and request identifiers are unique. A retry must point to its immediate
failed predecessor:

- rejection may be followed by `RETRY_AFTER_REJECTION` on the same schedule;
- timeout may be followed by `RETRY_AFTER_TIMEOUT` on the same schedule;
- a failed attempt may restart after a different schedule version;
- a pending attempt may be explicitly superseded by a schedule revision and
  restarted on that new version;
- response identities cannot be reused by a later attempt;
- an accepted attempt is immutable and terminal except for an explicit
  `VOID_AFTER_SCHEDULE_REVISION` record with a new schedule version and a
  schedule-conflict reason;
- a voided observation is terminal.

No retry count, duration, backoff, provider SLA, or network timeout is invented
by this contract. `timeout_policy_externally_established` is permanently false;
the future policy remains an explicit external design dependency.

## External authority dependencies

The following eight dependencies are represented separately and remain
externally unresolved:

1. provider authentication and commercial entitlement;
2. provider timestamp semantics;
3. exact jurisdiction/market identity;
4. DraftKings execution-state equivalence;
5. raw-response retention permission and provenance;
6. kickoff/rescheduling authority;
7. governance authorization;
8. effective-time/version authority.

Tests may provide identity-bound `SYNTHETIC_FIXTURE` dependencies to exercise
the complete contract. Such fixtures prove only local software behavior. They
must not be described as verified external facts or substituted for production
approval.

## Deliberately absent capabilities

There is no real evidence writer, manifest or ledger initializer, provider
client, credential lookup, database integration, collector, scheduler,
activation endpoint, order submission, or production wagering path. Adding any
of those requires a separate explicit authorization after the external and
governance prerequisites are resolved.
