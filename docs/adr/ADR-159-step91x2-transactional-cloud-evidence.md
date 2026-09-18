# ADR-159: Step 91X.2 transactional cloud evidence foundation

## Status

Accepted for implementation as a non-prospective candidate/shadow foundation.
Deployment and authority transition are not authorized.

## Decision

Step 91X.2 introduces a bounded operational evidence repository contract with
the existing JSONL functions retained as the local authority and regression
oracle. Google packages are optional and isolated from local commands. A
Firestore adapter may operate only in a candidate namespace.

The logical slot is the SHA-256 of canonical JSON containing `game_id`, market
type (`MONEYLINE` or `TOTALS`), and target label. The slot also retains kickoff,
frozen target center and bounds, schema, state, lease generation, raw identity,
and terminal canonical identities. Leases are per-slot, never global. An active
lease cannot be stolen; an expired lease can be taken over with an incremented
epoch; a stale owner cannot checkpoint or commit; terminal state is immutable.

## Accepted fetch/checkpoint boundary

A provider response becomes accepted source evidence only when its immutable,
sanitized raw checkpoint commits. A crash after receipt but before that commit
leaves no accepted evidence and a later invocation may refetch. This rule applies
only to the non-prospective cloud candidate and does not alter the formal
prospective protocol.

Raw evidence stores provider, lane/product, requested books, actual fetch time,
the relevant reproducible payload, payload hash, parser version, and bound slots.
It rejects API keys, authorization data, credential-bearing URLs, and secret-like
fields. One invocation record can bind multiple games. Truncation is forbidden;
an implementation must use deterministic chunks if a real response approaches
Firestore's document-size limit.

## Transactions and idempotency

Lease acquisition is a Firestore compare-and-set transaction. Raw checkpointing
validates owner and epoch and immutably binds the response to every included
slot. Canonical success atomically creates or exactly validates observation and
attempt documents and marks the slot terminal. Failed and missed attempts retain
the existing Step 91Q/R terminal behavior. Identical ambiguous retries are
accepted after full validation; conflicts fail closed and are never overwritten.

The provider call cannot participate in a Firestore transaction. Before fetch,
Firestore failure produces no provider call. After `RAW_CAPTURED`, derivation is
replayable without refetch. Concurrent delivery, Scheduler retries, Cloud Run
retries, expired leases, and delayed execution are resolved through the slot
state machine. Actual UTC invocation and provider timestamps remain authoritative.

## Provider and collection semantics

Existing parsers and canonical builders remain authoritative. HTTP retrieval is
separated from parsing so one h2h payload and one totals payload can each be
reused for all eligible games in an invocation. The two products are not merged.
The frozen DEF EPA builder, Week 1 neutral rule, Week 2 computed-zero behavior,
books, windows, math, recommendations, execution, closing, settlement, health,
and performance semantics remain unchanged.

## Export and authority

The only synchronization direction is Firestore to a validated JSONL cache.
Each export validates schemas, identities, and terminal linkage, canonically
sorts records, writes and fsyncs four files in a new immutable generation, then
atomically replaces a small `CURRENT` pointer. Previous generations remain.
Generated cache evidence is ignored by Git. No JSONL-to-Firestore path exists.

Local `data/operational` JSONL remains authoritative. Firestore is explicitly
`NON_PROSPECTIVE_CLOUD_CANDIDATE`; Step 91V/T/W do not automatically consume it.
Promotion requires a later reviewed shadow-comparison and human authorization.

## Security, scheduling, and cost

The future service is private. Scheduler has only Run Invoker; the separate
runtime identity has candidate Firestore access and Secret Accessor on the one
Odds API secret. Secret material is never persisted or returned. One future UTC
Scheduler job runs at minutes 7, 22, 37, and 52; actual execution time controls
eligibility, with no widened windows or backfill. The design is expected to fit
current free allowances, but billing and current pricing require explicit review
before deployment.

## Deployment and rollback

This change creates no Google resource and makes no API call. Emulator validation
is required before deployment. Rollback pauses Scheduler and preserves all cloud
evidence; local authority continues without model or historical rewrites.

## Step 91X.2A emulator validation

The adapter was validated against the official Cloud Firestore emulator 1.22.0
using Google Cloud CLI 585.0.0, Java 21, `127.0.0.1:8080`, and the isolated fake
project `demo-gridiron-step91x2a`. Tests exercised leases, takeover, stale-owner
rejection, raw recovery, atomic success and failure, exact replay, immutable
conflicts, namespace isolation, the 900 KB application guard, and real client
transaction callbacks.

The emulator uses pessimistic locks. Deliberately synchronized transactions can
all exhaust their bounded client retry budgets instead of guaranteeing a winner.
The adapter therefore re-reads only after an `Aborted`-caused retry exhaustion:
an existing competing slot is reported unavailable, while an unexplained failure
still fails closed. Slightly staggered duplicate deliveries produce exactly one
lease winner. Emulator validation does not replace later production shadow
validation of contention, latency, ambiguous network responses, or quotas.
