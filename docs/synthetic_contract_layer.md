# Synthetic contract layer — proposed interfaces

PROPOSED — REQUIRES EXPLICIT AUTHORIZATION for any extension beyond the authorized
synthetic implementation. This is unnumbered work, not a new project step.

## Boundary

`gridiron.market.synthetic_contracts` and `synthetic_lifecycle` are pure, in-memory
contracts. They are not integrated into the existing Core-Three preview, a CLI,
collector, original seven-book protocol, or historical diagnostics. They have no
network, credential, filesystem, manifest/ledger writer, activation or wagering
interface. Existing configurations and scientific parameters are unchanged.

`SYNTHETIC_VALID` means a deliberately fabricated test assertion, never externally
verified. A successful `simulate_activation_gate` result still has
`real_evidence_write_allowed=False` and `external_claims_authenticated=False`.
It is not a transferable production authorization token.

Provider authenticity, timestamp meaning, jurisdiction equivalence, DraftKings
account executability, retention permission, schedule authority, governance
approval and effective-time authority are each:

**NOT ESTABLISHED BY REPOSITORY EVIDENCE.**

## Interfaces

- Approval: exact protocol/version/variant/specification/build/configuration,
  action/scope, fixture authority, validity/revocation and all eight dependencies.
  Lifecycle acceptance independently replays a complete immutable gate context and
  binds its result to the pending game, response, approval and validation identities
  plus a canonical SHA-256 digest of every context field.
- Acquisition: attempt/request/game/provider-event/response identity, complete
  response, one receipt, nine components, provenance fingerprint, retention mode
  and fixture DraftKings prices. No HTTP or real provider-price parsing.
- Timestamps: original text and UTC; unresolved, observation and publication
  meanings remain distinct; receipt, clock, effectiveness and kickoff are separate.
- Schedule: source, fingerprint, retrieval/revalidation, exact game/kickoff,
  version/predecessor and availability. Revisions require an explicit, distinct,
  identity-matched predecessor in both gate validation and lifecycle replay.
  Predecessor artifacts and their ancestry are recursively checked for state, source,
  fingerprint, chronology and linkage. No NFLVerse authority claim.
- Execution: fixture feed/state/account/scope, availability/restrictions, expiry,
  same-response prices and independent jurisdiction/execution fixture claims.
- Retention: none, permitted, rejected/sanitized, review, qualifying simulation,
  manifest simulation and ledger simulation. No mode writes anything.
- Separation: historical/preview/prospective-fixture types and exact logical
  `synthetic://` namespace/schema pairs; no classification-based promotion or
  prospective-to-historical backward flow.
- Operations: structured failures and explicitly unset production policy values.
- Lifecycle: immutable replay and simulated compare-and-swap revisions; no store.
  Review attestations have distinct roles, subjects and artifacts. Finalization
  review identities are derived from the contract subject, approval dependency and
  validation identity. Finalization requires a separately established context identity,
  a `FINALIZE` approval and bound synthetic provenance.

## Fixture assumptions, not production decisions

Exact clock/receipt and execution-comparison time equality, state-specific
execution fixtures, and effective time preceding request start/receipt are
conservative simulation contracts. They do not approve a production clock,
jurisdiction, account equivalence or effective-time policy.

Pending attempts bind a schedule version. Revision cannot authorize an old pending
attempt. Supersession is the schedule predecessor/version relationship, never an
operation replacing accepted prices. Post-acceptance change requires void, with no
recapture. Cancellation is terminal. Finalization is a synthetic disposition with
a fixture reference, not an acquired result or computed win/loss.

The gate accepts immutable snapshots and supplied accepted-ID tuples. It is not a
transactional concurrency barrier. Lifecycle checks reject competing acceptance
on a shared history; separate memory forks are not production concurrency control.
Real trust, clock acquisition, durable replay protection, revocation freshness,
permission enforcement and atomic persistence require separate authorization.

New tests are deterministic and in-memory. They create no evidence files and
prove software behavior only. No historical performance informs scientific or
activation choices.
