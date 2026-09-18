# ADR-160: Step 91X.3 Google Cloud deployment readiness

## Status

Ready for a separately authorized candidate deployment. This ADR creates no
Google Cloud resource and does not promote cloud evidence to authority.

## Decision

Use a dedicated Google Cloud project and co-locate a private Cloud Run service,
Firestore Standard edition in Native mode, Cloud Scheduler, and an Artifact
Registry Docker repository in `us-central1`. Secret Manager uses automatic
replication because Cloud Run does not support regional secrets. Local JSONL
remains the only operational authority; Firestore begins empty and uses only the
existing `candidate_v1` namespace.

Cloud Run uses request-based billing, one vCPU, 512 MiB memory, concurrency one,
minimum instances zero, maximum instances one, and a five-minute request timeout.
One UTC Scheduler job runs `7,22,37,52 * * * *`, calls the private service with an
OIDC token, has a five-minute attempt deadline, and makes at most one retry. Actual
UTC invocation time remains authoritative. Delayed calls do not widen windows or
backfill missed evidence.

The deployment identity, runtime service account, and Scheduler invocation
service account are separate. The runtime receives `roles/datastore.user` and
Secret Accessor on the single Odds API secret. `roles/datastore.user` is broader
than the candidate collections because Firestore IAM has no predefined
collection-scoped data role; application namespace validation remains an
additional boundary. The Scheduler identity receives `roles/run.invoker` only on
the candidate service. Neither runtime identity receives Owner or Editor.

## Deployment-safety corrections

The build context now excludes Git data, operational evidence, caches, tests,
databases, output, environment files, and common credential/key filenames.
The image still includes the retained schedule explicitly required at runtime.

The entrypoint previously inspected ten Firestore slot documents for every
future scheduled game on every invocation, including games weeks away. A guard
now skips games above the largest frozen upper bound (780 minutes) before any
slot read. This preserves every frozen window and missed-window result while
keeping reads proportional to games approaching kickoff.

## Cost and workload

The logical season contains 2,400 lane/window slots. A continuously enabled
15-minute Scheduler job makes about 2,880 requests in a 30-day month and 10,752
requests over sixteen weeks. The far-future guard keeps ordinary Firestore usage
well below the naive 2,400 reads per invocation. Exact reads and writes remain
dependent on retries, contention, failures, and schedule clustering and must be
observed with budget alerts.

At this scale the design appears capable of fitting current free allowances,
including one of three free Scheduler jobs per billing account, Firestore's one
free Standard database per project with daily read/write allowances, Cloud Run's
free usage allowance, six active Secret Manager versions and 10,000 monthly
accesses, and 0.5 GiB of Artifact Registry storage. This is not a guarantee of
zero cost. Billing is required for the intended deployment, and image builds,
image storage, network transfer, log retention, accidental scaling, paid
Firestore features, and usage shared across the billing account can incur cost.

## Shadow validation and rollback

The candidate must run in shadow beside local JSONL. Compare canonical mapping,
window classification from comparable timestamps, provider timestamps, prices,
totals, identities, outcomes, retries, leases, checkpoints, and provider-call
counts. Market movement between independent collection times is not a defect.

Before any future authority discussion require at least two full NFL weeks,
every operational target label, both lanes, at least 100 terminal slots, at least
one controlled retry/replay, one expired-lease recovery exercise, zero immutable
conflicts, zero secret leakage, zero post-kickoff acceptance, and reconciliation
of every unexplained parser or identity discrepancy. Promotion requires a new
explicit governance decision.

Rollback pauses Scheduler first, preserves Firestore evidence and logs, stops
scheduled traffic, and leaves local JSONL authoritative. Candidate evidence is
never deleted, rewritten, backdated, or imported into formal prospective data.

