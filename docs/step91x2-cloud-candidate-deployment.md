# Step 91X.2 cloud candidate deployment plan

This document is a future deployment template, not deployment authorization.
Firestore remains candidate/shadow evidence only. Local JSONL remains the
operational authority.

## Required future resources

- One Google Cloud project with billing explicitly reviewed and authorized.
- One Firestore Standard default database in the selected Cloud Run region.
- One private, request-based Cloud Run service built from
  `Dockerfile.cloud-candidate`, with zero minimum instances and concurrency one.
- One Secret Manager secret containing `GRIDIRON_ODDS_API_KEY`.
- One runtime service account with only Firestore candidate-namespace access and
  Secret Accessor on that single secret.
- One separate Scheduler invoker account with only Cloud Run Invoker on the
  candidate service.
- One Cloud Scheduler job using an authenticated OIDC request.
- Artifact Registry for the candidate image.

No default Editor service account should be used. The service must reject public
unauthenticated requests. The runtime and scheduler identities must be distinct.

## Scheduler template

The future Scheduler expression is `7,22,37,52 * * * *` in UTC. It invokes the
private service every 15 minutes while avoiding minute zero. Delivery time is
not observation time; the Cloud Run invocation's actual UTC time is authoritative.
Frozen target centers and inclusive bounds remain unchanged. Delayed runs do not
widen windows or backfill observations.

## Candidate-only configuration

The Firestore namespace defaults to `candidate_v1`. There is intentionally no
configuration switch that promotes it to authority. Step 91V, Step 91T, and Step
91W continue to read local JSONL. A separately invoked exporter may create a
validated cache under an explicit `data/cloud_operational_cache` root, but it
never uploads JSONL to Firestore and never overwrites `data/operational`.

## Verification before any future deployment

Official Firestore emulator 1.22.0 validation completed in Step 91X.2A using an
isolated `demo-` project and local-only endpoint. Then run a reviewed shadow
period and compare actual timestamps,
provider timestamps, prices, target classification, identities, completeness,
retries, and failures with the local authority. Deployment, Scheduler creation,
secret creation, billing attachment, and authority transition each require
separate explicit authorization.

## Rollback

Pause Scheduler, deny invocation, and retain every cloud document. Do not delete,
merge, rewrite, or backfill evidence. Local JSONL remains available as authority;
no model or protocol change is involved.
