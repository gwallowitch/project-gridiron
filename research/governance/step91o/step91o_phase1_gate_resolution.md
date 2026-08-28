# STEP 91O — Phase 1 Pre-Freeze Gate Resolution

**PHASE 1 — NON-PROSPECTIVE / NON-EVIDENCE**

## Executive decision

Phase 1 resolves the deterministic specification items that do not require commercial access, but the Core-Four protocol remains **NOT READY TO FREEZE, IMPLEMENT, OR ACTIVATE**.

The blocking items are Bet365's final disposition, exact sportsbook/state jurisdiction, paid Caesars conformance, provider timestamp semantics, raw-response retention permission, authoritative kickoff provenance and rescheduling artifacts, DraftKings execution-state equivalence, commercial entitlement, implementation audit, and an effective timestamp.

No production source or configuration is changed. The original seven-book Step 91C–91I implementation remains frozen.

## Baseline and scope

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting HEAD: `b38b10482e3f8e944e52262f4ceeb33cd6fcfcf9`
- Starting tree: clean
- Classification: research/readiness only
- Design label: `step91k-2026-live-market-core-four-v1`
- Design status: unimplemented and inactive
- Candidate label: `market-plus-def-epa-capped-0425-v1 / step91k-core-four transportability variant`

## Sources reviewed

Repository evidence:

- Step 91M provider-conformance Markdown and JSON.
- Step 91N governance Markdown and JSON.
- Step 91C ledger and Step 91D ingestion.
- Step 91H integrity configuration and implementation.
- Step 91I configuration, schedule retention, operations, and tests.

Official external evidence:

- The Odds API v4 documentation: https://the-odds-api.com/liveapi/guides/v4/
- The Odds API bookmaker catalog: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
- The Odds API terms: https://the-odds-api.com/terms-and-conditions.html
- Bet365 official U.S. states page: https://www.bet365.com/hub/en-us/states
- Odds-API.io official documentation and catalog cited by Step 91M.
- OpticOdds official timestamp documentation cited by Step 91M.

Search snippets are not treated as evidence.

## Objective universe and Bet365

The outcome-independent eligibility rule from Step 91N is retained: a book must be a surviving original identity, operational and regulated in the U.S., cover the required NFL markets, have an exact stable provider identity and objectively established jurisdiction, expose usable timestamp semantics, and permit the approved audit/retention structure.

| Book | Operational | U.S. | NFL | ML | Spread | Total | Provider identity | Jurisdiction | Timestamp | Retention | Reproducibility | Phase 1 status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bet365 | PASS | PASS operationally | PARTIAL documented | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL | **PARTIAL** |
| BetMGM | PASS | PASS brand/operator | PASS non-evidence structure | PASS | PASS | PASS | PASS draft mapping | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL | **PARTIAL** |
| FanDuel | PASS | PASS brand/operator | PASS non-evidence structure | PASS | PASS | PASS | PASS draft mapping | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL | **PARTIAL** |
| Caesars | PASS | PASS brand/operator | PARTIAL catalog | PARTIAL | PARTIAL | PARTIAL | PASS catalog mapping | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL | **PARTIAL** |
| DraftKings | PASS | PASS brand/operator | PASS non-evidence structure | PASS | PASS | PASS | PASS draft mapping | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL | **PARTIAL** |

### Bet365 disposition

**PARTIAL — not obsolete and not finally excluded.**

Bet365 officially reports current U.S. operations. Provider A has no U.S. Bet365 key in its official catalog. Provider B documents generic `Bet365` and a regional `bet365 NJ` identity, but the available credential failed authentication in Step 91M. Provider C was not credential-tested. Required timestamp and retention evidence is absent.

Bet365 cannot be included now because it has not passed the same gates as the draft Core Four. It also cannot be finally excluded as technically unavailable until an authenticated regional provider test succeeds or demonstrates failure.

A later paid/authenticated test must establish all of the following without recording prices as evidence:

1. Exact regional U.S. Bet365 identifier and state.
2. Upcoming NFL event identity.
3. Two-sided moneyline, main spread, and main total.
4. Timestamp field and authoritative meaning.
5. Stable canonical team/outcome structure.
6. Permitted internal retention, hashing, and reviewer access.
7. Compatibility with the protocol's selected jurisdiction.

No replacement sportsbook is added.

## Jurisdiction contract

Minimum evidence for a U.S. feed requires both an exact provider identifier and authoritative provider documentation classifying that identifier in a U.S. region or named state. Brand name alone is insufficient.

Feed classes:

- `US_AGGREGATE`: provider explicitly assigns the key to `us`/`us2`, but no state is proven.
- `US_STATE_SPECIFIC`: provider identifies a named U.S. state and the operator is licensed there.
- `GLOBAL_UNQUALIFIED`: no jurisdiction encoded or documented; reject.
- `NON_US_REGIONAL`: UK, EU, AU, or another non-U.S. region; reject.
- `UNKNOWN`: conflicting or incomplete evidence; reject.

Provider A proves only `US_AGGREGATE` for the draft identifiers. Its documentation says `regions` determines returned bookmakers and names `us` and `us2` as United States regions, but does not establish a sportsbook's exact state. The optional source IDs may help with state/mobile variations but do not themselves prove an execution jurisdiction.

Status: **PARTIAL and blocking.** Before freeze, the protocol must name the intended execution state and obtain evidence that every source represents that state or formally approve an aggregate-market feature with a separately state-verified DraftKings execution quote.

## Provider mapping and canonicalization

Draft mapping:

| Canonical book | Provider | Exact key | Feed | Backup |
|---|---|---|---|---|
| BetMGM | The Odds API | `betmgm` | `us` | none |
| FanDuel | The Odds API | `fanduel` | `us` | none |
| DraftKings | The Odds API | `draftkings` | `us` | none |
| Caesars | The Odds API | `williamhill_us` | `us` | none |

Only exact keys count. Titles and aliases never establish identity. Unknown, duplicate, global, international, and wrong-region identities reject. One provider response may count each canonical book at most once.

Status: **PASS for the draft mapping; paid Caesars identity still requires live conformance before freeze.**

## Timestamp semantics

| Source field | Supported classification | Can prove ten-minute quote age? |
|---|---|---|
| The Odds API bookmaker `last_update` | Market/bookmaker update field; exact underlying event is undocumented | **UNKNOWN** |
| Odds-API.io market `updatedAt` | Market-update timestamp; polling versus price-change meaning unresolved | **UNKNOWN** |
| OpticOdds odd `timestamp` | Odds-change timestamp per official documentation | PARTIAL pending authenticated identity |
| OpticOdds `last-polled` | Polling timestamp, explicitly distinct from odds change | No, not alone |
| Local `receipt_at` | Local retrieval-completion timestamp | Yes for local chronology only |

The Odds API example schema exposes bookmaker `last_update`, but official documentation reviewed here does not say it is the time the underlying sportsbook price changed. It therefore cannot yet be assigned to `quote_at` for the ten-minute rule.

Status: **UNKNOWN and blocking.** Written provider clarification must define the field, clock source, update event, timezone, and behavior when a quote is unchanged. The frozen runtime rule remains: timestamp required, `quote_at <= receipt_at`, age no more than ten minutes, future or missing timestamp rejects, and HTTP latency is audit-only.

## Raw retention and provenance

The Odds API terms prohibit resale, repackaging, or redistribution as a standalone raw-data product and invite users to contact the provider when uncertain. They do not affirmatively resolve season-long internal raw retention, hashing, independent reviewer access, publication, Git inclusion, or post-subscription retention.

| Provider | Retention classification |
|---|---|
| The Odds API | **UNKNOWN** |
| Odds-API.io | **UNKNOWN** |
| OpticOdds | **UNKNOWN** for customer raw-copy rights |

Status: **UNKNOWN and blocking.** Written clarification must cover complete response storage, normalized extracts, hashes, duration, reviewer access, publication/sharing, Git inclusion, and deletion/retention after subscription. Absence of a prohibition is not permission. A reduced provenance substitute requires a separate governance approval. This is not legal advice.

## Kickoff authority and rescheduling

The existing artifacts are not internally sufficient to close this gate:

- Step 91H declares a retained NFL official schedule artifact.
- Step 91I schedule code actually retains an NFLVerse schedule with fixed source and derived SHA-256 values.

NFLVerse is useful provenance but is not the official NFL source named by the frozen integrity configuration. The discrepancy must not be silently reinterpreted.

Minimum deterministic contract:

1. Retain and hash an official NFL schedule artifact naming kickoff UTC, teams, week, and retrieval time.
2. Revalidate it immediately before the request and before accepting the response.
3. Provider `commence_time` must match the current authoritative kickoff.
4. A change detected before acceptance invalidates the old window and uses the new official kickoff.
5. Postponed/rescheduled games remain ineligible until a new official kickoff is retained and a valid window occurs.
6. Cancellation yields no qualifying capture.
7. A change discovered after acceptance requires a prospectively specified append-only void mechanism; no silent retention, rewrite, or discretionary recapture.
8. Authority outage and conflicting-source behavior must fail closed.

Status: **PARTIAL and blocking.** Policy direction is deterministic, but the official artifact acquisition and append-only void representation are not implemented or audited.

## Main-line, duplicate, and suspended behavior

- Moneyline: exactly one `h2h` market with exactly the canonical home and away outcomes; three-way markets reject.
- Spread: exactly one featured `spreads` pair with equal and opposite points; alternate or multiple pairs reject.
- Total: exactly one featured `totals` Over/Under pair at the same point; alternate or multiple pairs reject.
- Exact duplicate: collapse only when every canonical identity, line, price, and timestamp agrees.
- Conflict: reject the book and therefore the four-book consensus.
- Suspended/locked/null/unavailable/incomplete: treat as missing and reject the book.
- No price or line selection by an operator.
- Moneyline alone enters the model; spread and total remain contextual.

The Odds API featured market structure supports this deterministic contract. It does not expose a separately documented suspension flag in the reviewed standard response, so absence/null/incompleteness must fail closed.

Status: main-line and duplicate contract **PASS**; explicit suspension signaling **PARTIAL**, with deterministic fail-closed behavior resolved.

## Atomic capture and missing-book behavior

All four books and all requested markets must come from one completed event-scoped Provider A response. `receipt_at` is recorded after the entire body is received. No cached, cross-call, or cross-provider assembly is allowed.

Every consensus book requires one fresh, valid, two-sided moneyline. One missing, stale, suspended, wrong-jurisdiction, conflicted, or malformed book rejects the attempt. Three-of-four, imputation, later replacement, and favorable-price selection are prohibited.

Provider/network failure yields a retained rejected attempt only. An accepted capture is never replaced. Retries may occur only inside the existing 55–65-minute window and must each be retained, consistent with Step 91H; exact operational timeout and retry scheduling must be specified before first capture without changing the scientific thresholds.

Status: atomic and missing-book contract **PASS for readiness**; transport timeout/retry schedule remains an implementation-audit item.

## DraftKings execution-state equivalence

DraftKings remains both a consensus constituent and execution venue. Within the market snapshot, consensus and execution prices must be the identical `draftkings` h2h outcomes from the same atomic response.

Provider A's aggregate `us` classification does not prove that those prices equal the price executable in the operator's state/account. Exact execution state is not declared in the current protocol.

Status: **UNKNOWN and blocking.** Before freeze, name the execution state and either obtain provider confirmation/evidence of state equivalence or freeze a separate same-time state-specific DraftKings capture that does not replace the consensus quote. No execution change is authorized here.

## Provider fallback

**NO BACKUP PROVIDER.** A second provider is not required for v1. Provider failure rejects the attempt. This avoids provider-dependent price selection and cross-provider timestamp/normalization ambiguity.

Status: **PASS.** Any future backup requires a new protocol revision.

## Commercial entitlement and credit capacity

Classification: **REQUIRED FOR OPERATION, NOT AUTHORIZED FOR PURCHASE IN PHASE 1.**

Caesars `williamhill_us` is officially listed as paid-only. Since all four books are mandatory and there is no backup, the approved Core-Four protocol cannot operate through Provider A without the paid entitlement. Paid access does not resolve Bet365 because Provider A has no U.S. Bet365 key.

Before purchase, governance must resolve or expressly sequence the Bet365 disposition, written jurisdiction/timestamp/retention responses, exact plan entitlement, refund/cancellation terms, and authorization for a non-evidence paid Caesars test.

Conservative 20,000-credit check using the requested 240 captures:

- Base captures: `240 × 3 markets × 1 region = 720` credits.
- Two full retries for every capture: `1,440` credits.
- Sports discovery: zero credits under official documentation.
- Schedule/event discovery and conformance reserve: `200` credits.
- Settlement and operational overhead reserve: `640` credits.
- Conservative total: `3,000` credits.

Even doubling that total yields 6,000, so 20,000 credits is comfortably sufficient. This is capacity planning, not an instruction to purchase or increase request frequency.

## Pre-activation gates

| # | Gate | Status | Evidence | Blocking? | Exact resolution required |
|---:|---|---|---|---|---|
| 1 | Original protocol closure | PASS | Step 91N | Yes | None |
| 2 | New protocol identity | PASS | Step 91N distinct design/variant labels | Yes | None |
| 3 | Objective universe | PARTIAL | Equal eligibility rule exists; Bet365 application unresolved | Yes | Final equal-criteria universe decision |
| 4 | Bet365 | PARTIAL | Operational; provider conformance incomplete | Yes | Authenticated regional test or documented technical failure |
| 5 | U.S. jurisdiction | PARTIAL | Provider A proves aggregate U.S., not state | Yes | Name execution state and prove feed classification |
| 6 | Provider mapping | PARTIAL | Exact Core-Four keys documented | Yes | Paid live Caesars mapping test |
| 7 | NFL coverage | PARTIAL | Three books structurally tested; Caesars catalog only | Yes | Paid non-evidence Caesars NFL test |
| 8 | Market conformance | PARTIAL | Three books pass; Caesars untested | Yes | Caesars ML/spread/total structural pass |
| 9 | Timestamp semantics | UNKNOWN | `last_update` meaning insufficiently documented | Yes | Written provider clarification |
| 10 | Freshness | PASS | Deterministic chronology/ten-minute rule | Yes | None after timestamp gate passes |
| 11 | Main-line definition | PASS | Exact featured-market contract | Yes | None |
| 12 | Duplicate handling | PASS | Exact-collapse/conflict-reject contract | Yes | None |
| 13 | Suspended handling | PARTIAL | Fail-closed rule defined; explicit provider signal unclear | Yes | Confirm provider representation or retain absence/null rule |
| 14 | Atomic capture | PASS | One response, no assembly | Yes | Verify event-scoped response under paid entitlement |
| 15 | Kickoff authority | PARTIAL | Step 91H says official; Step 91I uses NFLVerse | Yes | Retained official NFL artifact and conflict/outage rule |
| 16 | Rescheduling | PARTIAL | Deterministic policy direction exists | Yes | Specify/audit append-only void behavior |
| 17 | DraftKings state equivalence | UNKNOWN | Aggregate U.S. is not state proof | Yes | Name state and verify executable equivalence |
| 18 | Fallback | PASS | No backup; failure rejects | Yes | None |
| 19 | Raw retention | UNKNOWN | Terms do not affirm required rights | Yes | Written permission or separately approved substitute |
| 20 | Commercial entitlement | FAIL | No paid plan, by design | Yes | Later authorization, purchase, and Caesars conformance |
| 21 | Implementation audit | FAIL | Core-Four is intentionally unimplemented | Yes | Implement only after freeze, then independently audit |
| 22 | Effective timestamp | FAIL | No active protocol | Yes | Set after every prior gate passes |

`FAIL` for gates 20–22 describes intentionally absent prerequisites; it is not authorization to resolve them during Phase 1.

## Resolution sequencing

### MUST RESOLVE BEFORE FREEZE

- Bet365 disposition and final objective universe.
- U.S./state jurisdiction contract.
- Paid Caesars market and identity conformance evidence, or a governance decision that reopens universe design.
- Provider timestamp semantics.
- Raw-retention permission or approved substitute.
- Official kickoff authority and rescheduling/void contract.
- DraftKings execution-state equivalence.
- Final canonical mapping and entitlement specification.

### MUST RESOLVE BEFORE PAID PURCHASE

- Written jurisdiction, timestamp, and retention responses sufficient to justify Provider A.
- Exact paid-plan capability and billing authorization.
- Approved non-evidence Caesars conformance procedure.
- Clear statement whether Bet365 testing requires a different provider entitlement.

### MUST RESOLVE BEFORE FIRST CAPTURE

- Frozen production specification and implementation.
- Focused and regression verification.
- Independent implementation audit.
- Empty/uninitialized new-protocol manifest and ledger paths.
- External effective timestamp strictly before the first attempt.
- Operational timeout/retry schedule and official schedule artifact availability.

### DOCUMENT / MONITOR

- Rejected attempts by failure reason.
- Provider availability and latency without changing thresholds.
- Quote-age distribution.
- Contextual spread/total availability.
- Credit usage.
- Schedule-change events.

Monitoring cannot change the frozen universe, consensus, thresholds, or provider during collection.

## Phase 1 conclusion

Phase 1 closes the provider mapping, no-backup, main-line, duplicate, atomic-response, missing-book, consensus, and credit-capacity design questions. It does not close the external facts that require provider statements or paid conformance.

Activation remains prohibited. No provider plan was purchased or activated; **$0 was spent**. No real manifest or ledger was initialized or modified. Prospective evidence remains zero. No qualifying capture, settlement, historical optimization, model recalibration, or 2026 outcome use occurred.
