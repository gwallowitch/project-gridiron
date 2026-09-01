# Post-91O prospective-readiness specification

## 1. Executive status

- Checkpoint: `eb55c358a99a4b68041211560a2a3da54b828aa5`
  (`feat: add isolated synthetic contract layer`).
- Branch: `feature/step91i-prospective-collection-operations`.
- Starting repository state: clean; local `HEAD` equalled the branch's local
  `origin` reference.
- Step 91O is complete as a governance, inactive implementation, remediation, and
  historical-diagnostic sequence. It specified and implemented the separate
  Core-Three transportability architecture, kept it non-prospective, hardened its
  deterministic contracts, and preserved the distinction between historical
  diagnostics and prospective evidence.
- The post-91O synthetic contract layer is also complete at this checkpoint as an
  unnumbered, isolated, in-memory representation. Its successful gate still reports
  `real_evidence_write_allowed=False` and
  `external_claims_authenticated=False`.
- Core-Three remains `IMPLEMENTED_INACTIVE`, with `activation_allowed=false` and
  `prospective_evidence_count=0` in
  `config/step91o_core_three_protocol_v1.json`.

The project is not waiting for another model experiment. It is waiting primarily for
external authority and governance evidence. Repository code can validate such evidence
after it exists; it cannot manufacture it.

## 2. Formal successor determination

**NO FORMALLY DEFINED SUCCESSOR FOUND.**

No Step 91P, Step 92, or other numbered successor is present in repository paths,
governance records, ADRs, source, tests, configuration, or Git history. Numeric `92`
matches found by broad search are unrelated data values or formatting widths. Git
history proceeds through Step 91O and then through unnumbered audits, hardening, and
the isolated synthetic contract layer.

The authoritative evidence is:

- `research/governance/step91o/step91o_phase2c_core_three_specification.md`
  defines the protocol but lists hard pre-activation gates.
- `research/governance/step91o/step91o_phase2d_engineering_readiness.md`
  authorizes only separately named, non-activating engineering and says real paths,
  effective time, and activation require later separate authorization.
- `research/governance/step91o/step91o_phase3_core_three_implementation.md`
  records a deliberately inactive implementation and ends with “Stop after Phase 3.”
- `docs/synthetic_contract_layer.md` calls the synthetic interfaces proposed,
  unnumbered, non-authoritative, and incapable of real writes or external
  authentication.
- `config/step91o_core_three_protocol_v1.json` explicitly records every material
  external gate as unresolved and activation as false.
- Commit `eb55c35` adds only the isolated synthetic layer; its message and file set do
  not define or authorize a successor.

Generic future-work language in these sources is a dependency inventory, not an
implementation or activation authorization.

## 3. Current architecture

### Original frozen candidate and seven-book protocol

The scientific candidate is `market-plus-def-epa-capped-0425-v1`. The original
prospective implementation in Steps 91C–91I encodes the seven-book market protocol,
DraftKings execution, frozen ledger/evidence concepts, audit/readiness logic, and
offline orchestration. Step 91N closed the original seven-book 2026 experiment. Its
implementation is an executable historical/governance record and must not be edited
into a Core-Three implementation or treated as current collection authority.

### Inactive Core-Three preview

Step 91O created a separate identity for BetMGM, FanDuel, and DraftKings, with exact
`h2h`, `spreads`, and `totals` requirements, one-response atomicity, equal one-third
no-vig consensus, exact event/kickoff reconciliation, same-object DraftKings prices,
and append-only lifecycle behavior. Its operations and CLI expose only sanitized,
offline, non-evidence preview behavior. They expose no real collector, manifest,
ledger, settlement, or evidence-writing command.

### Synthetic contract layer

`gridiron.market.synthetic_contracts` and `synthetic_lifecycle` model approval,
acquisition, timestamps, schedule ancestry, execution scope, retention modes, review
binding, activation dependencies, lifecycle, replay protection, and path separation.
They are pure and in-memory. SHA-256 structural bindings prove fixture consistency,
not authenticity or authority.

### Historical diagnostic layer

The 2025 Phase 4A/4B/4C artifacts are historical diagnostics only. They document
availability, leakage, provenance, and breakdown limitations. They are not
prospective observations, cannot enter a prospective evidence path, and cannot
authorize activation, sportsbook selection, coefficient changes, or wagering.

## 4. Frozen scientific boundary

The following must remain unchanged unless separately and explicitly governed outside
this specification:

- Candidate: `market-plus-def-epa-capped-0425-v1`.
- Market coefficient: `+4.980172`.
- DEF EPA coefficient: `+1.044827`.
- Intercept: `-2.514766`.
- Symmetric residual cap: `0.0425` (4.25%).
- Eligibility: strictly positive offered-price edge (`> 0%`).
- Original population rules, including their season/week and missing-data rules.
- Original seven-book consensus universe: Bet365, SI, Betway, BetMGM, FanDuel,
  Caesars, and DraftKings.
- DraftKings as the execution venue.
- Original Step 91C–91I protocol identities, schemas, paths, constants, artifacts,
  ledger behavior, and byte-hash regression boundary.
- Core-Three as the separate BetMGM/FanDuel/DraftKings, equal-one-third protocol;
  it must never be described as or merged into the original seven-book experiment.
- Core-Three status: inactive and non-evidence.
- Historical Phase 4A/4B/4C outputs: diagnostic, consumed, and non-prospective.
- No evidence pooling between original seven-book, Core-Three, preview, synthetic,
  or historical paths.

## 5. External blocker matrix

| Blocker | Why it matters | Repository can establish? | External authority required? | Evidence required | Activation consequence |
|---|---|---:|---:|---|---|
| Provider-origin authentication | A parsed response or hash does not prove who produced the market data. | No; it can validate a supplied signed/versioned package. | Yes | Written provider identity contract and authenticated response/source mechanism tied to the approved product/feed. | Without it, every acquisition remains unverified and must reject. |
| Provider timestamp semantics | Freshness arithmetic is meaningless until the update trigger and unchanged-quote behavior are known. | No; parsing proves syntax only. | Yes | Provider documentation or written clarification defining field, clock, trigger, timezone, polling/publication behavior, and unchanged quotes. | Timestamp-dependent capture remains blocked. |
| Jurisdiction/state equivalence | Aggregate U.S. branding does not prove a named market or state. | No | Yes | Approved jurisdiction definition plus provider/operator evidence binding each feed identity to the applicable state or an explicitly governed aggregate-feature rule. | Consensus inputs cannot qualify. |
| DraftKings account/location executability | Copied or same-object DraftKings prices do not prove availability to the execution account at its location. | No | Yes | Named state/account procedure and contemporaneous provider/operator evidence proving market and both prices are executable under the approved scope. | No qualifying decision or bet may be represented. |
| Retention/publication permission | Hashing, normalized retention, reviewer access, archival duration, and publication may have different rights. | No; code cannot interpret silence as permission. | Yes | Written permission matrix covering raw response, normalized extract, hashes, storage duration, reviewer access, publication/sharing, and post-entitlement handling. | No real capture or evidence writer may retain material. |
| Authoritative scheduling | Capture windows and void/revision behavior depend on an authoritative, versioned kickoff. | No; it can enforce a selected authority contract. | Yes | Approved official source, acquisition method, source/version identifiers, retrieval time, hashes, revalidation cadence, outage/conflict policy, and revision/cancellation semantics. | Any ambiguity, outage, or conflict fails closed. |
| Explicit governance approval | Passing code and synthetic tests do not authorize collection or evidence creation. | No | Yes | Named approval identity, protocol/build/configuration scope, permitted actions, dependency closures, revocation/expiry rules, and independent review acceptance. | Activation, real paths, and evidence writes remain prohibited. |
| Authoritative effective timestamp | A config date or caller clock cannot decide when prospective status begins. | No | Yes | Governance-issued effective instant, timezone, approval linkage, publication/receipt provenance, and rule requiring it to precede the first attempt. | Pre-effective observations are never prospective evidence. |

All eight blockers remain **NOT ESTABLISHED BY REPOSITORY EVIDENCE**.

## 6. Local engineering readiness matrix

“Specifiable locally” means a deterministic contract and synthetic tests can be
designed without asserting an external fact. It does not mean implementation is
authorized by this planning task.

| Area | Specifiable locally? | Current repository position | Authorized to implement now? | Required boundary |
|---|---:|---|---:|---|
| Contract schemas | Yes | Synthetic and inactive Core-Three schemas provide a strong base. | No | External fields remain unresolved states until supplied. |
| Trusted receipt structure | Yes | Receipt, provider, local clock, and kickoff concepts are separate in synthetic contracts. | No | The actual trusted clock/procedure needs governance approval. |
| Schedule conflict semantics | Yes | Exact identity, zero tolerance, revisions, voids, cancellations, and ancestry are modeled. | No | Authority selection and conflict priority remain external. |
| Timeout/retry policy | Yes | Failure classes exist; production numbers are intentionally unset. | No | Values, retry eligibility, backoff, and attempt identity must be prospectively approved. |
| Clock/effective-time representation | Yes | Types and chronology checks exist. | No | Clock trust and effective-time authority cannot come from configuration alone. |
| Retention-mode representation | Yes | Distinct synthetic modes and no-write behavior exist. | No | Allowed material, purposes, audiences, duration, and deletion require written permission. |
| Evidence identity model | Yes | Subject, approval, validation, context, response, and finalization bindings exist synthetically. | No | Real identity issuance and authority verification are absent. |
| Manifest/ledger contract definitions | Yes | Original seven-book append-only concepts are reusable as patterns, not implementations for Core-Three. | No | New Core-Three paths and schemas require separate authorization and must never mutate original artifacts. |
| Failure taxonomy | Yes | Deterministic failure classes and fail-closed behavior are locally testable. | No | Operational dispositions and retry rules require approval. |
| Dry-run/simulation behavior | Yes | Already isolated, deterministic, and non-evidence. | No broader work | It must retain no route to real paths, credentials, or activation. |
| Audit logging requirements | Yes | Required identities, timestamps, hashes, rejection reasons, and lifecycle events can be specified. | No | Retention and disclosure limits must be externally settled first. |
| Provider/network adapter | Structurally testable with fixtures | No real adapter exists or is authorized. | No | Provider authentication, entitlement, timestamp semantics, jurisdiction, and retention must close first. |
| Real evidence writer | Contract shape can be planned | Deliberately absent. | No | All external packages, governance approval, effective time, conformance, and independent audit must precede it. |

## 7. Activation dependency chain

The minimum dependency order is:

1. Preserve the frozen candidate, original seven-book record, and separate inactive
   Core-Three identity.
2. Obtain authentic closure packages for provider origin, timestamps, jurisdiction,
   DraftKings executability, retention, and scheduling.
3. Obtain explicit governance acceptance of those packages and freeze approved
   operational rules, including timeout/retry, trusted receipt, conflicts, retention,
   revocation, and effective-time semantics.
4. Finalize a versioned real-world contract whose protocol, build, configuration,
   evidence identity, paths, and authority inputs are exact and independently
   reviewable.
5. Implement trusted acquisition behind fail-closed gates without changing frozen
   science or original Step 91C–91I behavior.
6. Independently audit implementation, credentials isolation, clock behavior,
   permission enforcement, schedule lifecycle, replay protection, and failure paths.
7. Run a separately authorized, explicitly non-evidence conformance procedure and
   resolve every discrepancy without retrospective substitution.
8. Obtain a distinct activation approval and authoritative effective timestamp that
   precedes the first allowed attempt.
9. Only then may a separately authorized real prospective evidence path be initialized.

Synthetic tests address structural correctness at steps 4–6. They cannot supply the
external facts in steps 2–3, the conformance evidence in step 7, or the authority in
step 8. A synthetic success therefore cannot be promoted into real evidence.

## 8. Proposed future work sequence

These stages are planning labels only. They are not numbered project steps and do not
authorize implementation, purchasing, collection, or activation.

### Stage A — External authority acquisition

Obtain the eight closure packages, commercial entitlement evidence where applicable,
and named human/governance ownership. Resolve contradictions explicitly; absence of
evidence is failure, not implied approval.

### Stage B — Contract finalization

After Stage A, freeze versioned authority, acquisition, receipt, schedule, retention,
failure, evidence-identity, manifest/ledger, revocation, and effective-time contracts.
Record exact permitted actions separately for build, conformance, evidence-path
initialization, evidence writes, finalization, and activation.

### Stage C — Trusted acquisition implementation

Only under new implementation authorization, build the authenticated provider and
authoritative schedule interfaces, exact receipt procedure, permission-aware
provenance handling, and approved retry/conflict logic. Keep all output non-evidence.

### Stage D — Prospective evidence path

Under separate authorization, implement a new Core-Three manifest/ledger/evidence
path with atomic append, replay protection, credential isolation, lifecycle voids,
and zero-state verification. Do not reuse or rewrite the original seven-book paths.

### Stage E — Controlled conformance test

Under an approved procedure, exercise authenticated inputs without counting them as
prospective evidence. Audit source identity, timing, state/account execution,
schedule equality, retention, failure behavior, and complete provenance.

### Stage F — Only-if-authorized activation

Require independent audit acceptance, explicit activation approval, and an
authoritative future effective timestamp. Initialize real paths only after those
conditions hold. Production wagering remains outside this specification.

## 9. Stop conditions

Stop rather than proceed if any of the following occurs:

- No explicit scope authorizes the next action.
- Any external blocker is unknown, expired, revoked, conflicting, or merely inferred.
- Provider identity, entitlement, timestamp meaning, jurisdiction, execution scope,
  retention, schedule authority, governance identity, or effective time cannot be
  proven exactly.
- The authoritative schedule is unavailable, ambiguous, revised without provenance,
  or conflicts with provider identity/kickoff.
- A required book, market, outcome, timestamp, identity, or same-response binding is
  absent, duplicated, substituted, stale, future, or malformed.
- A proposed change would modify frozen coefficients, cap, eligibility, population,
  execution venue, original seven-book definitions, or historical artifacts.
- A historical, preview, rejected, dry-run, or synthetic object would enter a
  prospective path.
- A retry would replace an accepted observation or a schedule change would permit
  recapture contrary to the frozen lifecycle.
- Retention permission does not expressly cover the intended material and use.
- Tests pass but independent audit, conformance, activation approval, or effective
  time is absent.
- Any credential, network call, real path, manifest, ledger, or evidence write appears
  outside a separately authorized task.

## 10. Research-integrity rules

- Never promote retrospective, historical, preview, rejected, dry-run, or synthetic
  material into prospective evidence.
- Never pool Core-Three evidence with original seven-book evidence.
- Never recalibrate coefficients or intercepts from collection or diagnostic results.
- Never optimize thresholds, eligibility, residual cap, capture windows, or failure
  rules against observed outcomes.
- Never select sportsbooks or protocols based on observed historical ROI.
- Never treat hashes as provider authentication, parsing as timestamp authority,
  aggregate branding as jurisdiction proof, or copied prices as executability.
- Never authorize through caller flags, test fixtures, configuration booleans, or a
  successful synthetic gate.
- Never omit rejected attempts, missing observations, schedule failures, or no-bets
  from the audit record once a real record is separately authorized.
- Never use 2025 Phase 4A/4B/4C diagnostics as prospective evidence or as activation
  justification.
- Never enable production wagering under this work sequence.

## 11. Recommended next Codex task

There is no presently authorized engineering successor. The immediate action is to
stop and obtain explicit external/governance closure scope.

After all eight closure packages are supplied and formally accepted, the smallest
legitimate Codex task would be an **unnumbered, non-activating contract-finalization
audit** that:

1. verifies each supplied package's identity, scope, dates, provenance, revocation
   state, and relationship to the frozen Core-Three protocol;
2. maps those accepted facts into a proposed versioned authority/receipt/schedule/
   retention/operational/evidence contract;
3. defines deterministic acceptance and rejection tests using sanitized fixtures;
4. proves original Step 91C–91I and historical artifacts remain unchanged; and
5. stops before network implementation, real paths, conformance execution, evidence
   creation, activation, or wagering.

That recommendation is not implementation authorization. A new explicit prompt must
name the accepted external packages, authorized actions, exact files, verification,
and stop conditions before Codex changes anything beyond planning.
