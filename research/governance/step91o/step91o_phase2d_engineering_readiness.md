# STEP 91O — Phase 2D Core-Three Engineering-Readiness Audit

**CORE-THREE — ENGINEERING / GOVERNANCE — NON-PROSPECTIVE / NON-EVIDENCE**

## Decision

Core-Three can be implemented cleanly without altering frozen seven-book behavior, but only as a separate versioned implementation. The existing Step 91C–91I modules are intentionally coupled to the original protocol ID, seven-book tuple, schemas, paths, and assertions. Parameterizing or editing them in place would weaken the strongest available regression boundary.

Engineering status: **PARTIAL / NEW COMPONENTS REQUIRED**. Implementation may begin only as non-activating code and tests. Activation remains blocked by provider timestamp semantics, raw-retention permission, jurisdiction, DraftKings state equivalence, official kickoff authority, and explicit governance approval.

No Caesars access or paid provider plan is required for the engineering work described here.

## Baseline and scope

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting local and remote HEAD: `8f5530e994d81e926c7a2e5053602707bc35f8d7`
- Starting tree: clean
- All Step 91M–91O Phase 2C governance was read and not modified.
- API requests, credits, provider purchases, prospective artifacts, and outcome use: zero.

## Repository ownership boundary

### A. Frozen seven-book implementation — DO NOT TOUCH

- `config/step91c_prospective_data_capture_v1.json` through `config/step91i_prospective_collection_operations_v1.json`
- `src/gridiron/market/prospective_ledger.py`
- `src/gridiron/market/prospective_market_ingestion.py`
- `src/gridiron/market/prospective_audit.py`
- `src/gridiron/market/prospective_evidence.py`
- `src/gridiron/market/prospective_readiness.py`
- `src/gridiron/market/prospective_integrity.py`
- `src/gridiron/market/prospective_schedule.py`
- `src/gridiron/market/prospective_operations.py`
- `scripts/step91c_ledger.py` through `scripts/step91i_collection.py`
- Their existing `tests/test_market_prospective_*.py` suites and frozen reports/ADRs

These files explicitly encode `step91b-prospective-validation-v1`, seven books, `complete_seven_book_input`, permissive aliases, moneyline-only ingestion, latest-observation selection, NFLVerse schedule retention, and unconditional content-addressed raw retention. They are the closed experiment's executable record.

### B. Protocol-neutral reusable infrastructure

- `src/gridiron/market/moneyline.py`: reuse `american_odds_to_implied_probability` and `remove_two_sided_vig` directly.
- Standard-library ISO timestamp parsing, SHA-256, canonical JSON, and append-only concepts are reusable patterns. Avoid importing private frozen helpers merely to share code; either add a genuinely protocol-neutral utility in a separately reviewed change or implement small Core-Three-local equivalents.
- Existing frozen tests remain regression oracles and must continue passing byte-for-byte behavior assertions.

### C. New Core-Three implementation

Use a separate namespace and separate config/evidence paths. Proposed files are listed in the file-level plan below. Nothing in this audit creates them.

### D. Governance/research

`research/provider_conformance/step91m/`, `research/governance/step91n/`, and `research/governance/step91o/` are evidence-boundary and decision records. Production code must consume a future frozen config, not parse prose governance files at runtime.

## Audit findings

### Provider universe and mapping

Seven-book assumptions occur in `CONSENSUS_BOOKS` and validation/error paths in `prospective_ledger.py`; `BOOK_ALIASES`, `_validate_contract`, normalization, and canonical ordering in `prospective_market_ingestion.py`; `FROZEN_PROTOCOL`, completeness checks, and dry-run fixtures in `prospective_operations.py`; audit/evidence/readiness modules; all Step 91C–91I configs; scripts that import those modules; and their tests.

Core-Three must define immutable ordered canonical books `("BetMGM", "FanDuel", "DraftKings")` and exact provider mapping `betmgm`, `fanduel`, `draftkings`. No case folding, display-title lookup, `BOOK_ALIASES`, generic identity, regional substitution, or unknown/extra key is accepted. Request metadata must record the exact key filter and jurisdiction classification. The parser must treat the provider title as descriptive only.

### Market normalization and main lines

The existing Step 91D schema accepts only `market == "moneyline"` with home/away odds and cannot represent provider event IDs, bookmaker/market SIDs, region, h2h/spread/total objects, points, suspension, or response metadata. It has no main-spread or main-total selector.

The new adapter must enforce Phase 2C literally: one exact `h2h`, `spreads`, and `totals` market per book; two canonical outcomes; opposite spread points; matching total points; numeric prices/points; no alternate keys; and reject duplicates, conflicts, suspensions, malformed or incomplete outcomes. There is no selection among multiple lines. Multiple candidates are ambiguity and reject.

### Consensus

`prospective_ledger.py` uses a fixed seven-book tuple, fixed ordering, seven-book completeness, and arithmetic division by the tuple length. `prospective_market_ingestion.py` asserts that exact contract before parsing. `prospective_operations.py`, `prospective_evidence.py`, `prospective_audit.py`, and `prospective_readiness.py` independently assert it.

Core-Three needs a separate consensus implementation using the protocol-neutral two-sided vig removal and an exact arithmetic mean of three home probabilities, one-third each. Candidate coefficients remain unchanged. A new ledger event must carry the distinct Core-Three protocol and evidence labels. Do not make `CONSENSUS_BOOKS` configurable inside the old module.

### Atomic capture and observation selection

The old ingestion accepts a list of normalized offers and selects the maximum `observed_at` per book. Identical latest duplicates collapse; conflicting latest duplicates reject. That can combine independent source observations and violates the Phase 2C one-response boundary.

The old collection CLI consumes a file rather than an authenticated response envelope. `capture_game` can operate on one file, but cannot prove that its offers originated in one event-scoped response or that nine markets were captured together.

The new adapter must parse exactly one immutable response envelope and attach a generated response-attempt ID and one `receipt_at` to all contained objects. It must never accept arrays assembled across calls. Any duplicate bookmaker or market rejects, even if identical. Acquisition, parsing, validation, decision preview, and append are distinct stages; no rejected response can become evidence.

### Timestamps and freshness

Reusable behavior: existing timestamp parsers require timezone awareness and normalize UTC; `prospective_integrity.py` calculates a ten-minute age and rejects future observations.

Deficiency: current code consumes caller-supplied `observed_at`, not Provider A `last_update`, and cannot preserve the provider's exact timestamp string or provenance. It assumes the supplied observation time is semantically suitable. Core-Three can safely implement strict ISO parsing, UTC normalization, chronology checks, receipt timing, and a feature flag/gate that refuses activation while timestamp semantics are unapproved. It cannot label `last_update` odds-change time without written provider evidence.

The provider semantic question is a **provider/governance blocker**, not solvable in code. Engineering must make the unresolved state fail closed rather than invent meaning.

### Kickoff and event identity

`prospective_schedule.py` constructs canonical IDs from season/week/team abbreviations, converts NFLVerse Eastern timestamps, and requires exact retained hashes. `prospective_operations.initialize_manifest` records that schedule; `capture_game` verifies only the raw canonical game identity and pre-kickoff relationship. It does not ingest Provider A event ID/home/away/`commence_time`, compare provider kickoff with the retained schedule, or revalidate an authoritative source immediately before acceptance.

The implementation also labels the retained kickoff as official although its adapter source is NFLVerse. It has no tolerance check because it performs no provider/schedule kickoff equality check. Schedule entries are immutable once registered, so revisions conflict rather than append a revision.

Core-Three needs exact one-to-one team mapping, provider event ID uniqueness, exact home/away orientation, and zero-tolerance kickoff equality against a separately retained official NFL artifact. The 00:15Z/00:20Z fixture must deterministically reject. No nearest-time or fuzzy fallback is permitted.

### Rescheduling lifecycle

Existing integrity/operations code supports appended `postponed`, `cancelled`, and `unavailable` status events. It does not define `SCHEDULE_REVISION` or `DECISION_VOID_SCHEDULE_CHANGE`, cannot attach old/new schedule hashes, cannot invalidate an accepted decision without settlement semantics, and treats a differing reinitialization as conflict.

Core-Three requires new append-only event schemas and replay transitions. Postponed blocks capture; pre-acceptance reschedule appends a revision and creates a new window; post-acceptance change appends a non-qualifying void and forbids recapture; cancellation is terminal without win/loss. No existing event is mutated.

### Jurisdiction and DraftKings execution

Existing schemas have a free-form provider string but no region, state, jurisdiction class, bookmaker SID, execution-state field, or verification provenance. They cannot establish more than the caller's assertion.

Core-Three should represent `US_AGGREGATE`, `US_STATE_SPECIFIC`, `NON_US`, `GLOBAL_UNQUALIFIED`, or `UNKNOWN` and reject unapproved classes. Which class is scientifically permitted and whether DraftKings matches a named executable state are provider/governance decisions. Engineering can store and enforce approved declarations; it cannot prove them.

DraftKings separation is conceptually reusable: old code includes DraftKings in consensus and copies or validates separate execution prices. However, `_execution_prices` permits supplied execution values that can differ from the DraftKings consensus observation. Core-Three must derive execution values from the identical atomic DraftKings h2h object, never accept separate/later values, and retain state-equivalence provenance. The code can prove same-object identity, not account/state executability.

### Raw retention and evidence boundary

`prospective_integrity.record_capture_attempt` reads the entire raw file, computes SHA-256, creates the artifact directory, and writes `{digest}.json` before parsing, freshness, or acceptance. Every malformed/rejected attempt is therefore retained raw. `prospective_operations` later relies on that artifact for interrupted-append recovery.

This is incompatible with Phase 2C while raw archival permission is unknown. New code must default to no raw write, compute any permitted hash in memory, retain only approved normalized/provenance fields, and make raw storage an explicitly frozen permission mode. It must not reuse the old recovery design until retention rights are resolved. Credential/query secrets must be removed before any metadata serialization.

### Failure-mode coverage

The old architecture fails closed for seven-book missingness, invalid American odds, future/naïve times, mismatched normalized teams, conflicting latest duplicates, stale age, capture window, duplicate decisions, and some terminal statuses. It does not cover the Core-Three exact-key universe, extra book, nine-market completeness, alternate/duplicate market objects, suspension encoding, Provider A event identity, provider/schedule kickoff equality, jurisdiction, same-object atomicity, state execution, permission-aware retention, or reschedule/void transitions.

## File-level future implementation plan

| File path | Current responsibility / problem | Proposed future change | Frozen behavior affected? | Required tests | Class | Risk |
|---|---|---|---|---|---|---|
| `config/step91c_prospective_data_capture_v1.json` through `config/step91i_prospective_collection_operations_v1.json` | Frozen seven-book contracts | No change | No | Existing suites remain green; hash/constant regression | DO NOT TOUCH | Critical |
| `src/gridiron/market/prospective_*.py` | Frozen ledger, ingestion, audit, evidence, readiness, integrity, schedule, operations | No behavior change | No | Entire existing prospective suite | DO NOT TOUCH | Critical |
| `scripts/step91c_ledger.py` through `scripts/step91i_collection.py` | Frozen CLI entry points | No change | No | Existing CLI tests | DO NOT TOUCH | High |
| `src/gridiron/market/moneyline.py` | Pure American-odds and no-vig math | Import unchanged from new consensus module | No | Existing moneyline plus Core-Three fixed fixtures | REUSE | Low |
| `config/step91o_core_three_protocol_v1.json` | Does not exist | New immutable protocol, mappings, markets, gate flags, paths, evidence class; activation false | No | Exact config/schema/tamper tests | NEW COMPONENT | High |
| `src/gridiron/market/core_three_types.py` | Does not exist | Frozen dataclasses/enums for event, book, markets, provenance, jurisdiction, rejection codes | No | Exact keys/types/serialization | NEW COMPONENT | Medium |
| `src/gridiron/market/core_three_provider.py` | No Provider A adapter | Parse one response envelope; exact keys; nine markets; preserve timestamps/SIDs; sanitize metadata; reject ambiguity | No | All mapping/market/atomic failure fixtures | NEW COMPONENT | High |
| `src/gridiron/market/core_three_consensus.py` | Seven-book mean is embedded in frozen ledger | Three-book no-vig mean and immutable candidate transformation under distinct ID | No | One-third weighting, ordering, numeric fixtures | NEW COMPONENT | High |
| `src/gridiron/market/core_three_schedule.py` | NFLVerse-only frozen adapter; no Provider A reconciliation | Read approved official artifact; exact team table/event reconciliation; zero kickoff tolerance; schedule hashes | No | event/home-away/kickoff/ambiguity/outage | NEW COMPONENT | Critical |
| `src/gridiron/market/core_three_integrity.py` | Frozen raw-first retention and event schema | New append-only chain, permission-aware provenance, attempt/revision/void transitions, activation gate | No | chain tamper, retention modes, lifecycle replay, no evidence leakage | NEW COMPONENT | Critical |
| `src/gridiron/market/core_three_ledger.py` | Seven-book protocol/ledger hard-coded | Distinct Core-Three decision/settlement schemas and validation; no reuse of old evidence paths | No | duplicate/orphan/immutability/execution identity | NEW COMPONENT | Critical |
| `src/gridiron/market/core_three_operations.py` | Old orchestration assumes seven-book file and raw artifact | Orchestrate preview/reject/dry-run only until gates; later atomic capture behind approval/effective-time guards | No | gate refusal, retries, same-response binding, dry-run isolation | NEW COMPONENT | Critical |
| `scripts/step91o_core_three.py` | No Core-Three CLI | New explicit validate/preview/dry-run commands first; activation commands disabled until later governance | No | CLI errors, canonical output, no default real paths | NEW COMPONENT | High |
| `tests/test_core_three_provider.py` | Does not exist | Exact three books and all market/failure fixtures | No | Mapping, market, duplicates, alternates, suspension, atomicity | NEW COMPONENT | High |
| `tests/test_core_three_consensus.py` | Does not exist | Fixed math and invariant tests | No | One-third mean, missingness, DraftKings role | NEW COMPONENT | High |
| `tests/test_core_three_schedule.py` | Does not exist | Official artifact/reconciliation/lifecycle fixtures | No | 00:15/00:20 rejection, reschedule, cancellation | NEW COMPONENT | Critical |
| `tests/test_core_three_integrity.py` | Does not exist | Provenance, hashing, retention and append-only transitions | No | No raw write, secret scan, tamper, void | NEW COMPONENT | Critical |
| `tests/test_core_three_operations.py` | Does not exist | End-to-end synthetic/non-evidence orchestration | No | Fail closed, no manifest/ledger leakage, activation refusal | NEW COMPONENT | Critical |
| `tests/test_core_three_frozen_separation.py` | Does not exist | Protect original protocol while new code exists | No | Old constants/config hashes/results unchanged; distinct paths/IDs | NEW COMPONENT | Critical |
| Future Core-Three ADR and frozen governance config | No implementation decision record | Add only after governance approves implementation scope | No | Documentation/config consistency | BLOCKER | High |

No existing frozen file needs modification. If implementation reveals a truly protocol-neutral defect, fix it only through a separately scoped change with proof that seven-book behavior and artifacts are unchanged; do not mix that repair into Core-Three implementation.

## Test architecture

Reusable tests are patterns, not fixtures to mutate:

- Ledger immutability, canonical JSON, corrupt-line, duplicate decision, and settlement tests from `test_market_prospective_ledger.py`.
- Timestamp, stale, hash-chain, window, status, and deterministic serialization patterns from `test_market_prospective_integrity.py`.
- Strict schema, unknown-key, malformed odds, order invariance, and no-mutation patterns from `test_market_prospective_market_ingestion.py`.
- Dry-run isolation, interrupted append, explicit identity, and workflow patterns from `test_market_prospective_operations.py`.
- Schedule hash, timezone, duplicate identity, write-once, and exact-universe patterns from `test_market_prospective_schedule.py`.

New Core-Three tests must cover exactly three books; each missing book; extra book; unknown/case/title/generic alias; duplicate bookmaker; missing/duplicate/alternate/conflicting/suspended/malformed h2h, spread, or total; event ID/team/home-away/kickoff mismatch; 00:15Z versus 00:20Z; timezone parsing; missing/future/stale timestamp; semantic-gate refusal; one-response atomicity; three-book no-vig consensus; same-object DraftKings execution; jurisdiction rejection; postponed/rescheduled/cancelled/void replay; permission-off raw non-retention; credential absence; dry-run separation; effective-time guard; and full old-protocol regression.

## Recommended implementation order

1. Freeze an engineering-only Core-Three config schema with `activation_allowed=false`, exact IDs, paths, and gate flags.
2. Add immutable Core-Three types and deterministic rejection codes.
3. Build a pure Provider A response parser using synthetic fixtures only; no network or evidence writes.
4. Add three-market normalization and adversarial parser tests.
5. Add pure three-book consensus using `moneyline.py`; prove fixed one-third weighting and unchanged coefficients.
6. Add official schedule artifact interface and exact provider-event reconciliation; retain the known mismatch regression.
7. Add permission-aware provenance and append-only attempt/schedule-revision/void chain.
8. Add distinct Core-Three ledger and same-object DraftKings execution validation.
9. Add orchestration that supports validate/preview/dry-run while refusing activation on unresolved gates.
10. Run all new tests plus the complete original Step 91C–91I regression suite and config/hash separation checks.
11. Conduct an independent implementation audit against Phase 2C.
12. Only after provider/governance gates close, separately authorize real paths, effective timestamp, and activation.

Timestamp semantics, retention permission, official kickoff authority, jurisdiction, and DraftKings state equivalence may be resolved in parallel with engineering. Production code must represent them as closed gates, not assumptions.

## Paid-provider decision

All engineering tasks use synthetic sanitized fixtures and the already observed free Core-Three schema. Caesars is outside the Core-Three universe. No paid conformance is required for config design, parsing, markets, consensus, atomicity, lifecycle, provenance, tests, or regression audit.

**Paid provider conformance is not the next necessary gate. Do not purchase or activate Caesars.**

## Final readiness table

| Area | Status | Classification | Required action |
|---|---|---|---|
| Frozen seven-book preservation | READY | DO NOT TOUCH | Enforce full regression and separation tests |
| Protocol-neutral odds math | READY | REUSE | Import unchanged |
| Core-Three config/identity | PARTIAL | NEW COMPONENT | Implement versioned inactive config |
| Provider universe/mapping | PARTIAL | NEW COMPONENT | Exact-key parser and rejection tests |
| Three-market normalization | BLOCKED | NEW COMPONENT | Implement Phase 2C schema |
| Main-line selection | READY design | NEW COMPONENT | Enforce exactly one featured market; no selection |
| Three-book consensus | READY design | NEW COMPONENT | Implement separate one-third mean |
| Atomic capture | PARTIAL | NEW COMPONENT | Bind single response envelope and receipt |
| Latest-observation removal | BLOCKED | BLOCKER | New parser must never use frozen latest-selection path |
| Timestamp parsing | READY concept | REUSE | Strict raw ISO text and UTC normalization |
| Timestamp semantics/freshness | UNKNOWN | BLOCKER | Written provider clarification; fail closed in code |
| Event identity | PARTIAL | NEW COMPONENT | Exact provider/official reconciliation |
| Kickoff reconciliation | BLOCKED | BLOCKER | Official source plus zero-tolerance implementation |
| Rescheduling/void | BLOCKED | NEW COMPONENT | Append-only schemas and replay transitions |
| Jurisdiction | UNKNOWN | BLOCKER | Provider/governance evidence; store approved class |
| DraftKings same-object separation | READY design | SMALL CHANGE | New ledger derives execution from atomic object |
| DraftKings executable state | UNKNOWN | BLOCKER | External evidence; cannot be solved by code |
| Raw retention | BLOCKED | BLOCKER | Permission decision and no-write default |
| Normalized provenance/hashes | READY design | NEW COMPONENT | Implement sanitized canonical record |
| Failure-mode handling | PARTIAL | NEW COMPONENT | Implement exhaustive rejection codes/tests |
| Evidence boundary | READY concept | NEW COMPONENT | Separate paths/classes; inactive gates |
| Test architecture | READY plan | NEW COMPONENT | Add five focused suites plus separation regression |
| Paid Caesars dependency | READY | DO NOT TOUCH | None; no purchase |
| Activation readiness | BLOCKED | BLOCKER | Provider, governance, implementation, audit, effective time |

## Final safety report

- Money spent: **$0**
- Provider plan purchased: **NO**
- Caesars activated: **NO**
- API requests: **0**
- Prospective evidence: **0**
- Manifest: **untouched**
- Ledger: **untouched**
- Candidate: **unchanged**
- Coefficients: **unchanged**
- Thresholds: **unchanged**
- Residual cap: **unchanged**
- Execution venue: **unchanged**
- Original seven-book protocol: **unchanged**

Stop after Phase 2D. Do not implement, freeze, activate, initialize evidence paths, or purchase provider access.
