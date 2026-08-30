# STEP 91O — Phase 2A Free-Only Provider / Implementation Conformance

**PHASE 2A — FREE-ONLY — NON-PROSPECTIVE / NON-EVIDENCE**

## Decision

Free testing resolves the structural conformance of BetMGM, FanDuel, and DraftKings for one upcoming NFL event. It does not resolve Caesars, Bet365, state jurisdiction, provider timestamp semantics, raw-retention rights, or DraftKings execution-state equivalence. The existing production architecture is the frozen original seven-book implementation and is not ready to consume the proposed Core-Four result.

**STOP AFTER PHASE 2A.** The Core-Four protocol remains not frozen, not implemented, and not activated.

## Baseline and boundaries

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting HEAD: `9329ff21808e6af585e68435c3f94a14ce2dee06`
- Starting tree: clean
- Credential presence was checked without displaying the credential.
- Prior Step 91M, Step 91N, Step 91O Phase 1, and Step 91O pre-purchase artifacts were read and not modified.
- No raw response or odds values were retained.

## Minimal free test

Two event-scoped Provider A calls were made on 2026-08-28 to observe repeat timestamp behavior. Both returned HTTP 200. Each requested one event, region `us`, exact keys `betmgm,fanduel,draftkings,williamhill_us`, and markets `h2h,spreads,totals`, with source IDs requested.

- Event ID: `8c94552d022acec4a0458d70c19d3da9`
- Event: New England Patriots at Seattle Seahawks
- Provider commence time: `2026-09-10T00:15:00Z`
- Calls: 2
- Credits used: 6 (three per call)
- Quota header moved from 42 implied prior usage to 48 used; 452 remained after the second call.
- Response scope was one event; each returned bookmaker was represented inside that completed event response.

| Key | Objects per response | Markets | Outcome structure | Points | Prices | Duplicate/conflict | Result |
|---|---:|---|---|---|---|---|---|
| `betmgm` | 1 | h2h, spreads, totals | two outcomes in each | numeric on spreads/totals | numeric and non-null | none observed | PASS |
| `fanduel` | 1 | h2h, spreads, totals | two outcomes in each | numeric on spreads/totals | numeric and non-null | none observed | PASS |
| `draftkings` | 1 | h2h, spreads, totals | two outcomes in each | numeric on spreads/totals | numeric and non-null | none observed | PASS |
| `williamhill_us` | 0 | none | unavailable | unavailable | unavailable | none | PAID_REQUIRED |

The moneyline names matched the two event teams; spreads matched the two event teams; totals were Over and Under. Each outcome exposed a source-ID field. No outcome deep-link field, jurisdiction field, suspension/availability field, null price, alternate market key, multiple line pair, duplicate bookmaker, or conflicting line was observed. Absence in this sample does not prove how the provider represents suspension, alternates, or conflicts.

## Deterministic main-line and failure mechanics

The requested featured keys produced exactly one `h2h`, one `spreads`, and one `totals` object per returned book, each with one complete pair. The response therefore supports deterministic selection by exact market key plus exact outcome contract for this sample. Alternate keys must be excluded; multiple same-key market objects or multiple line pairs must reject rather than be selected by price or operator judgment.

Missing, null, malformed, suspended, or incomplete outcomes remain missing. A missing mandatory book rejects the attempt. The free entitlement's absent Caesars object demonstrates the missing-book path but cannot demonstrate paid Caesars conformance. No explicit suspension field was observed, so suspended encoding remains PARTIAL.

## Timestamp and freshness mechanics

Every returned market exposed `last_update`; all three markets within a book shared the same displayed value in both near-consecutive calls, and the values did not change between calls. This demonstrates stable field presence and market-level placement in this sample only. It does not identify the underlying update trigger.

The inspection shell converted provider date values before reporting them, losing a safe representation of the original timezone suffix. A naïve subtraction then inherited a local offset and generated impossible negative ages. Those computed ages are invalid and are not retained as findings. This demonstrates an implementation requirement: preserve the raw timestamp string, require an explicit timezone, normalize to UTC, and only then calculate `quote_age = receipt_at - provider_timestamp`. Missing timezone, future time, or age above ten minutes must reject.

The arithmetic is deterministic once an authoritative timezone-aware timestamp exists, but Provider A documentation still does not establish whether `last_update` is sportsbook price-change, provider-observation, poll, or publication time. The frozen freshness check therefore cannot operate without unsupported semantic assumptions. Status: **UNKNOWN / REQUIRES DOCUMENTATION**.

## Event and kickoff reconciliation

Team identity and week reconcile deterministically to retained schedule row `2026_01_NE_SEA`. Kickoff does not: the provider sample was `00:15Z`, while the retained Step 91I NFLVerse schedule is `00:20Z`, a five-minute conflict. Under the approved equality rule this sample must reject.

This is also an authority conflict: Step 91H names a retained official NFL schedule, while Step 91I retains NFLVerse. Phase 2A does not change authority. Official artifact acquisition, revalidation, outage/conflict behavior, and append-only post-acceptance void/rescheduling events remain unresolved.

## DraftKings and Bet365

DraftKings passed provider, event, market, numeric-field, and source-ID structure. The bookmaker object also exposed a `sid`. It exposed no deep-link or jurisdiction field. The response cannot establish that the aggregate `us` quote equals the executable quote in a named state/account. DraftKings execution-state equivalence remains **UNKNOWN**.

Provider A's governed catalog mapping still exposes no legitimate state-specific U.S. Bet365 identity, and no such identity appeared in the tested Core-Four request. Generic, UK, European, or Australian Bet365 may not substitute. Bet365 remains **PARTIAL / REQUIRES GOVERNANCE**; it is not classified obsolete.

## Implementation audit

No production code was modified. The following are **IMPLEMENTATION BLOCKERS** for eventual Core-Four work:

1. `prospective_ledger.py`, `prospective_market_ingestion.py`, and `prospective_operations.py` enforce the original seven-book universe and original protocol ID.
2. The ingestion boundary accepts title aliases; the Core-Four contract requires exact provider keys and region provenance.
3. The existing input schema supports moneyline only, not normalized featured spread/total context, provider event ID, region, bookmaker/market source IDs, or provider response metadata.
4. Duplicate handling selects the latest timestamped observation and collapses identical latest rows; Core-Four prohibits cross-call assembly and requires conflicts within one atomic response to reject.
5. The current integrity layer writes a content-addressed raw artifact before validation. Core-Four raw retention is not authorized while licensing remains UNKNOWN.
6. The current schedule adapter retains NFLVerse identifiers and kickoff data, not the official NFL artifact named by Step 91H, and the tested kickoff conflicted by five minutes.
7. The runtime checks freshness on normalized `observed_at`, but no Provider A adapter exists to preserve and semantically validate `last_update` before mapping it to that field.
8. No state-specific DraftKings execution-equivalence input or audit field exists.
9. No Core-Four reschedule/void event contract or implementation exists.

Existing strengths that can be reused after governance freeze include strict timezone-aware normalized timestamps, fail-closed missing-book checks, pre-kickoff/window checks, append-only chains, DraftKings price separation, and content hashing. Reuse requires a new governed implementation; the frozen Step 91C–91I code must not be silently repurposed.

## Final gate table

| Gate | Status | Classification | Finding |
|---|---|---|---|
| BetMGM | PASS | RESOLVED FOR PHASE 2 | One object; three featured markets; complete numeric pairs |
| FanDuel | PASS | RESOLVED FOR PHASE 2 | One object; three featured markets; complete numeric pairs |
| DraftKings | PASS | RESOLVED FOR PHASE 2 | Provider structure and SIDs pass; execution state is separate |
| Caesars | PAID_REQUIRED | REQUIRES PAID TEST | `williamhill_us` absent under free entitlement |
| Bet365 | PARTIAL | REQUIRES GOVERNANCE | No legitimate verified U.S. Provider A identity |
| U.S. jurisdiction | PARTIAL | REQUIRES DOCUMENTATION | Aggregate `us` only; no state field observed |
| Timestamp semantics | UNKNOWN | REQUIRES DOCUMENTATION | Field present and stable; update trigger unproven |
| Raw retention | UNKNOWN | REQUIRES DOCUMENTATION | Required rights not affirmatively granted |
| Kickoff reconciliation | FAIL | REQUIRES GOVERNANCE | Provider and retained schedule differ by five minutes |
| Rescheduling | PARTIAL | REQUIRES ENGINEERING | Policy direction exists; void lifecycle absent |
| Main-line selection | PASS | RESOLVED FOR PHASE 2 | Exact featured keys yielded one complete pair each |
| Duplicate handling | PARTIAL | REQUIRES ENGINEERING | Provider sample clean; existing latest-selection behavior is incompatible |
| Suspended handling | PARTIAL | REQUIRES DOCUMENTATION | No explicit signal observed; fail-closed rule remains |
| Atomic capture | PARTIAL | REQUIRES ENGINEERING | Provider response supports it; Core-Four adapter absent |
| DraftKings execution state | UNKNOWN | REQUIRES DOCUMENTATION | No jurisdiction/deep-link proof in response |
| Commercial entitlement | PAID_REQUIRED | REQUIRES PAID TEST | Free entitlement cannot return Caesars |

## Safety statement

- Money spent: **$0**
- Plan purchased: **NO**
- Subscription activated: **NO**
- Prospective evidence: **0**
- Real manifest: **untouched**
- Real ledger: **untouched**
- 2026 outcomes used: **NO**
- Candidate changed: **NO**
- Coefficients changed: **NO**
- Thresholds changed: **NO**
- Residual cap changed: **NO**
- Execution venue changed: **NO**

Activation remains prohibited. Phase 2A ends here; the next paid-only item is the separately authorized minimal Caesars test.
