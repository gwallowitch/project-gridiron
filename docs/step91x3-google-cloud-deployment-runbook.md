# Step 91X.3 Google Cloud candidate deployment runbook

This is a future mechanical plan, not current deployment authorization. Do not
run the resource-changing sections without explicit approval. Local JSONL stays
authoritative and the cloud classification stays
`NON_PROSPECTIVE_CLOUD_CANDIDATE`.

## 1. Prerequisites and placeholders

Use a dedicated project rather than an unrelated existing project. In a new
PowerShell session set placeholders; never place a secret value in these
variables or in command history.

```powershell
$ProjectId = "<GRIDIRON_GCP_PROJECT_ID>"
$BillingAccount = "<GRIDIRON_BILLING_ACCOUNT>"
$Region = "us-central1"
$Repository = "gridiron-candidate"
$Service = "gridiron-cloud-candidate"
$RuntimeSa = "gridiron-candidate-runtime"
$SchedulerSa = "gridiron-candidate-scheduler"
$Secret = "gridiron-odds-api-key"
$Job = "gridiron-candidate-quarter-hour"
$ImageTag = "079e1b5"
```

The future operator must first confirm permission to create a dedicated project,
attach billing, enable services, administer Cloud Run/Firestore/Scheduler/
Artifact Registry/Secret Manager, create service accounts, and act as the runtime
and Scheduler identities. Create a small monthly budget and alerts at 50%, 90%,
and 100%; budgets alert but do not cap spending.

Keep setup privileges on the human deployment/admin identity only and remove
temporary grants afterward. Depending on organization policy, the bounded setup
roles are Project Creator, Billing Account User, Service Usage Admin, Project IAM
Admin, Service Account Admin, Service Account User on the two created identities,
Cloud Run Admin, Cloud Build Editor, Artifact Registry Administrator, Cloud
Datastore Owner for database creation, Secret Manager Admin, and Cloud Scheduler
Admin. An existing project Owner can perform most setup, but Owner/Editor must
never be assigned to either workload identity.

## 2. Read-only preflight

These commands are safe discovery checks. Review every result before continuing.

```powershell
gcloud version
gcloud auth list
gcloud projects describe $ProjectId
gcloud billing projects describe $ProjectId
gcloud services list --enabled --project=$ProjectId
gcloud firestore databases list --project=$ProjectId
```

Do not set `GOOGLE_APPLICATION_CREDENTIALS` on Cloud Run. Its user-managed
runtime service account supplies Application Default Credentials.

## 3. Future project and API preparation

The required APIs are Resource Manager, Service Usage, IAM, Cloud Run,
Firestore, Secret Manager, Artifact Registry, Cloud Scheduler, Cloud Build, and
Cloud Logging. The creation commands below are intentionally recorded but were
not executed in Step 91X.3.

```powershell
gcloud projects create $ProjectId --name="Project Gridiron Candidate"
gcloud billing projects link $ProjectId --billing-account=$BillingAccount
gcloud config set project $ProjectId
gcloud services enable run.googleapis.com firestore.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com cloudbuild.googleapis.com iam.googleapis.com iamcredentials.googleapis.com logging.googleapis.com serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project=$ProjectId
```

## 4. Future identities and Firestore

Create a Standard edition Firestore database in Native mode, empty, in
`us-central1`. Do not import JSONL or enable TTL, PITR, backup, clone, or restore.
Default single-field indexes are sufficient because access is by deterministic
document identity or bounded collection enumeration; no composite index is
currently required.

```powershell
gcloud iam service-accounts create $RuntimeSa --display-name="Gridiron candidate runtime" --project=$ProjectId
gcloud iam service-accounts create $SchedulerSa --display-name="Gridiron candidate Scheduler invoker" --project=$ProjectId
gcloud firestore databases create --database="(default)" --location=$Region --type=firestore-native --edition=standard --project=$ProjectId
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$RuntimeSa@$ProjectId.iam.gserviceaccount.com" --role="roles/datastore.user"
```

`roles/datastore.user` is database-wide and therefore broader than the desired
candidate collection namespace. Do not grant it to the Scheduler identity. The
application must retain its fixed `candidate_v1` namespace and lack any authority
promotion switch.

## 5. Future secret creation

Grant access only to the runtime identity. Enter the Odds API key directly in
Google Cloud Console Secret Manager, or use a temporary local file created
outside the repository and securely remove that file afterward. Never paste the
key into chat, a command argument, PowerShell history, Firestore, logs, or the
container image.

```powershell
gcloud secrets create $Secret --replication-policy=automatic --project=$ProjectId
gcloud secrets add-iam-policy-binding $Secret --member="serviceAccount:$RuntimeSa@$ProjectId.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor" --project=$ProjectId
```

Pin the deployed environment variable to a numbered secret version. Rotate by
adding a version and deploying a new revision pinned to that version; disable the
old version only after validation.

## 6. Future image build

The repository `.dockerignore` bounds the uploaded context. Before building,
repeat the credential/context scans and verify `data/operational` is excluded.
Use the reviewed Dockerfile explicitly and co-locate Artifact Registry.

```powershell
gcloud artifacts repositories create $Repository --repository-format=docker --location=$Region --description="Non-prospective Gridiron candidate" --project=$ProjectId
$Image = "$Region-docker.pkg.dev/$ProjectId/$Repository/gridiron-cloud-candidate:$ImageTag"
$BuildConfig = @'
steps:
- name: gcr.io/cloud-builders/docker
  args: ['build','-f','Dockerfile.cloud-candidate','-t','${_IMAGE}','.']
images: ['${_IMAGE}']
'@
$BuildConfig | gcloud builds submit . --config=- --project=$ProjectId --substitutions="_IMAGE=$Image"
```

If the installed `gcloud` version does not accept the PowerShell stdin form,
stop and create a reviewed temporary Cloud Build configuration outside the
repository; do not improvise a source deployment that ignores the reviewed
Dockerfile.

## 7. Future private Cloud Run deployment

Deploy with request-based billing, no public access, concurrency one, zero warm
instances, maximum one instance, one vCPU, 512 MiB, and a five-minute timeout.
The Functions Framework process listens on Cloud Run's injected `PORT`.

```powershell
$RuntimeEmail = "$RuntimeSa@$ProjectId.iam.gserviceaccount.com"
gcloud run deploy $Service --image=$Image --region=$Region --platform=managed --service-account=$RuntimeEmail --no-allow-unauthenticated --concurrency=1 --min=0 --max=1 --cpu=1 --memory=512Mi --timeout=300 --set-secrets="GRIDIRON_ODDS_API_KEY=$Secret:1" --project=$ProjectId
$ServiceUrl = gcloud run services describe $Service --region=$Region --project=$ProjectId --format="value(status.url)"
```

Cloud Run responses must contain only classification, authority, invocation time,
bounded counts, status, and exception type. Never log or return request headers,
credential-bearing URLs, raw provider payloads, or exception text that embeds
requests. Diagnostic logs may contain invocation ID, canonical game and slot IDs,
target label, bounded state transition, and error category. Canonical source and
attempt evidence belongs in Firestore, not logs.

## 8. Future Scheduler binding and job

Grant `roles/run.invoker` on this service only. Use OIDC with the exact service URL
as audience. One job at minutes 7, 22, 37, and 52 UTC avoids minute zero. The
five-minute deadline matches Cloud Run. One retry with a 60-second minimum and
300-second maximum backoff is bounded before the next normal run.

```powershell
$SchedulerEmail = "$SchedulerSa@$ProjectId.iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding $Service --region=$Region --member="serviceAccount:$SchedulerEmail" --role="roles/run.invoker" --project=$ProjectId
gcloud scheduler jobs create http $Job --location=$Region --schedule="7,22,37,52 * * * *" --time-zone="UTC" --uri=$ServiceUrl --http-method=POST --oidc-service-account-email=$SchedulerEmail --oidc-token-audience=$ServiceUrl --attempt-deadline=300s --max-retry-attempts=1 --min-backoff=60s --max-backoff=300s --max-doublings=0 --project=$ProjectId
```

Scheduler delivery is not observation time. Every delivery recalculates
eligibility from actual UTC. Step 91X.2 leases prevent concurrent ownership;
terminal slots reject duplicates; `RAW_CAPTURED` retries derive from retained
payload without another provider call. A crash before raw checkpoint may refetch,
as already governed. There is no backfill.

## 9. Empty-start and shadow verification

Verify Firestore begins empty under `candidate_v1`; do not seed it. The expected
collections are `candidate_v1_collection_slots`,
`candidate_v1_raw_provider_responses`,
`candidate_v1_moneyline_observations`, `candidate_v1_moneyline_attempts`,
`candidate_v1_totals_observations`, and `candidate_v1_totals_attempts`.

For at least two full NFL weeks and 100 terminal slots, compare overlapping local
and cloud opportunities by game, target, comparable collection time, window,
bookmaker timestamps, prices/totals, canonical identities, classifications,
retries, leases, raw identity, and provider-call count. Exercise a controlled
retry/replay and expired-lease recovery. Independent timestamps can legitimately
produce market movement; parser or mapping differences on the same raw payload
cannot. Any secret leak, immutable conflict, duplicate accepted slot,
post-kickoff acceptance, current/future DEF EPA leakage, or local-authority write
blocks any authority discussion.

## 10. Rollback

Pause first; do not delete evidence.

```powershell
gcloud scheduler jobs pause $Job --location=$Region --project=$ProjectId
gcloud run services update $Service --region=$Region --max=1 --project=$ProjectId
```

Preserve Firestore candidate documents and Cloud Logging records, export for
audit only if authorized, and stop scheduled traffic. Local JSONL remains the
authority. Do not rewrite, merge, backdate, or promote cloud evidence.
