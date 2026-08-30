# STEP 91O — Phase 2C Core-Three Specification and Implementation Gap Audit

**CORE-THREE — NON-PROSPECTIVE / NON-EVIDENCE**

## Executive decision

This document defines the deterministic draft specification for a new Core-Three transportability protocol. The specification is complete wherever repository evidence and public provider documentation permit. Activation remains blocked by provider timestamp semantics, raw-retention rights, jurisdiction and DraftKings execution-state evidence, kickoff governance, implementation, testing, approval, and an effective timestamp.

**Core-Three is not frozen, implemented, or activated.** The original seven-book protocol remains closed and unchanged.

## Baseline and safety boundary

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting local and remote HEAD: `f4d9a5114662b44b6c85686d8eb2dfdc44c6ab3c`
- Starting tree: clean
- Prior Step 91M–91O artifacts were read and not modified.
- No API request was necessary: Phase 2B already supplied current two-event non-evidence conformance data.
- No production source, configuration, schedule, manifest, ledger, or evidence artifact was modified.

## 1. Protocol identity and immutable candidate

- Draft protocol ID: `step91o-2026-live-market-core-three-v1`
- Status: `DRAFT_SPECIFICATION_ONLY`
- Candidate variant label: `market-plus-def-epa-capped-0425-v1 / step91o-core-three transportability variant`
- Evidence class if later activated: `REAL PROSPECTIVE DATA — STEP91O CORE-THREE V1`
- Population: 2026 NFL regular season, Weeks 1–16.
- Capture window: 55–65 minutes before authoritative kickoff.
- Maximum quote age: ten minutes, conditional on closure of timestamp semantics.
- Execution venue: DraftKings.

The immutable candidate values are market coefficient `4.980172`, DEF EPA coefficient `1.044827`, intercept `-2.514766`, and residual cap `0.0425`, with strictly positive edge eligibility. They are not recalibrated here. The changed three-book market feature makes Core-Three a new estimand; unchanged coefficients do not make it equivalent to the original seven-book experiment.

## 2. Exact book universe and provider mapping

| Canonical book | Provider | Exact key | Permitted provider classification |
|---|---|---|---|
| BetMGM | The Odds API | `betmgm` | documented aggregate U.S. feed only |
| FanDuel | The Odds API | `fanduel` | documented aggregate U.S. feed only |
| DraftKings | The Odds API | `draftkings` | documented aggregate U.S. feed only |

Only the three exact, case-sensitive keys are accepted. Titles, normalized titles, aliases, generic identities, global identities, international variants, and state assumptions do not establish identity. An absent required key, repeated key, unknown key, extra bookmaker, or unresolved mapping rejects the entire attempt. No sportsbook substitution is allowed.

The request contract must retain sanitized request metadata proving sport `americanfootball_nfl`, the exact three-book filter, and the intended U.S. classification. Provider documentation says `bookmakers` takes priority when both `bookmakers` and `regions` are supplied; therefore `regions=us` plus an explicit bookmaker list is not independent proof of jurisdiction. Written provider classification remains required.

## 3. Three-market contract

Every required book must contain exactly one of each market in the same event response:

1. Moneyline: exact key `h2h`; exactly two outcomes; names equal the canonical home and away teams; no draw; both American prices numeric and valid.
2. Main spread: exact key `spreads`; exactly the home and away outcomes; both prices numeric; both points numeric, non-null, equal in magnitude, and opposite in sign.
3. Main total: exact key `totals`; exactly `Over` and `Under`; both prices numeric; both points numeric, non-null, and equal.

Keys such as `alternate_spreads` and `alternate_totals` never substitute. A duplicate bookmaker, duplicate market key, multiple line pair, three-way moneyline, unexpected outcome, null or malformed value, conflicting duplicate, explicit suspension/lock/unavailability, or incomplete pair rejects the attempt. No latest, best, closest, most balanced, or operator-selected line is permitted. Exact duplicates also reject rather than collapse, preserving an unambiguous one-object contract.

All three markets are required for a valid Core-Three observation. Moneyline is the only model input; spread and total are mandatory contextual audit fields.

## 4. Core-Three consensus

For American odds `a`:

- if `a > 0`, implied probability is `100 / (a + 100)`;
- if `a < 0`, implied probability is `-a / (-a + 100)`.

For each book:

`p_home_book = implied_home / (implied_home + implied_away)`

Core-Three market consensus:

`mean(p_home_BetMGM, p_home_FanDuel, p_home_DraftKings)`

Each constituent has weight `1/3`. All three valid, fresh, two-sided moneylines are mandatory. Two-of-three, imputation, reweighting, trimming, median, cross-call replacement, and favorable-price selection are prohibited. Cross-book price differences are constituent information, not duplicate conflicts. Conflicts mean multiple incompatible records for the same canonical book/market/response identity.

The existing candidate transformation then consumes this new market feature with the immutable coefficients. Because the feature and accepted-game population differ from seven-book collection, results must be reported only under the distinct Core-Three identity.

## 5. Atomic capture

One candidate observation is exactly one successfully completed event-scoped Provider A HTTP response containing all three exact books and all nine required market objects.

- The authoritative game is selected before the request.
- No earlier response, later response, cache, second provider, or operator input may supply a missing field.
- `request_started_at` is audit metadata.
- `receipt_at` is trusted local UTC immediately after the complete body is received and before parsing-dependent acceptance.
- Every object must share the response's exact provider event ID and canonical teams.
- The response is evaluated against the authoritative kickoff and 55–65-minute receipt window.
- There is no assembly interval because assembly is forbidden.
- No response-duration tolerance, network timeout, retry count, or retry schedule is invented here. Those operational values require prospective specification before activation. Every retry is a separate rejected or accepted attempt inside the same window; an accepted attempt is never replaced.

Any HTTP, decoding, schema, identity, market, book, timestamp, freshness, jurisdiction, or kickoff failure produces only a rejected attempt. No qualifying evidence exists until all gates and the future effective timestamp pass.

## 6. Timestamp and freshness contract

Provider field: exact raw ISO-8601 `last_update` attached at the documented response level used by the adapter. Local field: `receipt_at` in UTC.

Required parsing rules:

- Preserve the provider timestamp text before framework coercion.
- Require an explicit timezone and normalize to UTC.
- Reject missing, malformed, ambiguous, or future timestamps.
- Compute `quote_age = receipt_at - provider_timestamp`.
- Require `quote_age <= 10 minutes` for every required book/market object.
- Use zero clock tolerance unless a later prospective governance decision supplies evidence for another value.

Provider documentation establishes ISO formatting and field placement, but does not establish whether `last_update` represents sportsbook price change, provider observation, polling, or publication, nor unchanged-quote behavior. It therefore cannot yet be assigned protocol `quote_at` semantics. **Timestamp semantics and operational freshness are UNKNOWN, hard pre-activation gates.** Arithmetic readiness does not close semantic validity.

Source: https://the-odds-api.com/liveapi/guides/v4/

## 7. Event identity and kickoff authority

Authoritative identity is the unique retained official NFL schedule row containing season, season type, week, canonical home team, canonical away team, and kickoff UTC. Provider reconciliation requires all of:

- one unique provider event ID;
- exact canonical home/away identities after a separately frozen one-to-one team-code table;
- no home/away reversal;
- exact equality between provider `commence_time` and the current authoritative kickoff;
- uniqueness among all in-scope authoritative and provider events.

Fuzzy name, date-only, nearest-time, or manual matching is prohibited. A conflict or inability to prove uniqueness rejects.

Step 91H names a retained official NFL schedule artifact, but Step 91I actually derives its retained artifact from NFLVerse. This mismatch is unresolved. For Patriots–Seahawks, current NFL and Seahawks sources plus NFLVerse show `00:20Z`; Provider A repeatedly showed `00:15Z`. The difference is not timezone conversion and no legitimate revision explains it. Strict reconciliation is **FAIL** for that event; the cause remains **UNKNOWN**. There is no acceptable metadata tolerance. Five minutes cannot be silently waived because the capture window depends on kickoff.

Sources: https://www.nfl.com/schedules/2026/by-week/week-1 ; https://www.seahawks.com/schedule/2026/

Before activation, governance must approve an official artifact acquisition, retrieval timestamp, hashing, revalidation, outage, and conflict contract.

## 8. Postponement, rescheduling, and cancellation

All lifecycle changes are append-only:

- Postponed before acceptance: append `GAME_POSTPONED`; no capture until an official new kickoff exists.
- Rescheduled before acceptance: append `SCHEDULE_REVISION` containing old/new kickoff, source identifiers and hashes, and detection time. The old capture window becomes invalid; evaluate only the new window.
- Rescheduled after acceptance but before kickoff: append `DECISION_VOID_SCHEDULE_CHANGE`; retain the decision as non-qualifying and do not recapture under v1.
- Cancelled: append `GAME_CANCELLED`; no qualifying observation and no settlement as a win/loss.
- Authority outage or conflicting official artifacts: reject/fail closed.

No event, decision, schedule, or evidence record is overwritten. The named event schemas and replay invariants require implementation and independent audit before activation.

## 9. Jurisdiction and DraftKings execution

Jurisdiction classes:

- `US_AGGREGATE`: provider-classified U.S. market without state proof;
- `US_STATE_SPECIFIC`: documented named state and stable provider identity;
- `NON_US`: UK, EU, AU, or other non-U.S. regional identity;
- `GLOBAL_UNQUALIFIED`: brand without a jurisdiction contract;
- `UNKNOWN`: incomplete or conflicting evidence.

Current BetMGM, FanDuel, and DraftKings evidence is at most `US_AGGREGATE`. No response field observed in Phase 2B established a state. Non-U.S., global, and unknown classifications reject. Governance must either approve aggregate U.S. quotes as the consensus feature while separately proving execution, or require a common named state.

DraftKings remains both a one-third consensus constituent and execution venue. Its consensus and execution prices must be the identical h2h outcomes from the same atomic bookmaker object; no later or more favorable price may replace them. This ensures snapshot consistency but not executability. Sufficient closure evidence is a named execution state plus written provider/operator evidence or a controlled contemporaneous non-evidence comparison showing the provider source ID and both side prices correspond to the user's state/account market under a predeclared procedure. Until then: **UNKNOWN and blocking**.

## 10. Retention and provenance

Required normalized record and provenance, subject to provider permission:

- protocol/schema versions and evidence class;
- authoritative game ID, provider event ID, teams, kickoff, schedule source/hash/retrieval time;
- exact provider, region classification, bookmaker and market keys, source IDs;
- normalized outcomes, prices, points, and preserved provider timestamps;
- request category and sanitized parameters, HTTP status, receipt time, latency, quota cost;
- deterministic accept/reject status and reason codes;
- canonical extract hash and, only if permitted, complete-response hash and storage pointer.

The API key is never retained. Raw payloads are not placed in Git. Provider terms prohibit standalone resale/repackaging/redistribution and direct uncertain users to contact the provider, but do not affirm complete-response archival, season/post-subscription retention, hashing, reviewer access, or publication. **Raw retention permission remains UNKNOWN and blocking.**

If raw retention is denied, governance must separately approve a canonical normalized extract plus sanitized provenance and an in-memory response hash. The current implementation cannot be used because it writes content-addressed raw bytes before validation.

Source: https://the-odds-api.com/terms-and-conditions.html

## 11. Fail-closed decision table

| Condition | Result |
|---|---|
| Any required book missing | REJECT ATTEMPT |
| Extra, unknown, aliased, or duplicate book | REJECT ATTEMPT |
| Any required market missing, extra, duplicate, alternate, suspended, or malformed | REJECT ATTEMPT |
| Incomplete or conflicting outcomes/lines | REJECT ATTEMPT |
| Timestamp missing, invalid, future, stale, or semantically unapproved | REJECT ATTEMPT |
| Event/team/kickoff identity mismatch | REJECT ATTEMPT |
| Jurisdiction unknown or prohibited | REJECT ATTEMPT |
| Provider/network/decoding failure | REJECT ATTEMPT |
| DraftKings selected-side execution price unavailable | REJECT ATTEMPT / NO BET |

There is no two-book consensus, imputation, replacement book, backup provider, cross-call assembly, or retrospective recovery.

## 12. Implementation gap audit

| Area | Existing state | Classification | Required production work |
|---|---|---|---|
| Append-only chain and hashing concepts | Implemented for seven-book protocol | READY concept | Reuse under distinct Core-Three schemas after retention approval |
| Numeric odds and timezone-aware parsing | Implemented for normalized inputs | READY concept | Preserve exact provider strings and extend errors/provenance |
| Capture window and ten-minute arithmetic | Implemented | READY concept | Gate use on timestamp semantic closure |
| Provider universe/protocol identity | Seven books hard-coded across ledger, readiness, evidence, audit, operations | NEW COMPONENT | Separate Core-Three constants/config; do not mutate old protocol |
| Provider aliases | Permissive title aliases accepted | SMALL CHANGE in new adapter | Exact provider keys only; unknown/extra reject |
| Provider adapter | Network-independent file interface only | NEW COMPONENT | Event-scoped The Odds API adapter with sanitized metadata |
| Market normalization | Moneyline-only input schema | NEW COMPONENT | Exact h2h/spreads/totals schemas and pair validation |
| Observation selection | Selects latest per book and collapses identical latest rows | BLOCKER | One-response object identity; any duplicate/conflict rejects |
| Raw retention | Writes raw bytes before parsing/acceptance | BLOCKER | Permission-aware retention boundary; no raw write by default |
| Event reconciliation | Canonical game plus NFLVerse IDs; no Provider A mapping | NEW COMPONENT | Exact team table, provider event ID, official schedule equality |
| Kickoff authority | Config says NFL official; adapter retains NFLVerse | BLOCKER | Official acquisition/hash/revalidation and conflict policy |
| Rescheduling | Statuses exist; no schedule revision/decision-void schema | NEW COMPONENT | Append-only lifecycle events and replay validation |
| Freshness | Normalized `observed_at` checked | BLOCKER | Provider semantic approval and `last_update` adapter |
| Atomic capture | Integrity path can retain and process one file | NEW COMPONENT | Bind one response, receipt, three books, nine markets, no assembly |
| Consensus | Seven-book equal mean hard-coded | NEW COMPONENT | Separate three-book mean and distinct protocol identity |
| DraftKings separation | Consensus and execution fields exist | SMALL CHANGE | Enforce same atomic object and add state-equivalence provenance |
| Evidence boundary | Real/synthetic labels and append-only controls exist | SMALL CHANGE | New evidence class, paths, zero-state guard, effective-time guard |

The frozen Step 91C–91I implementation must remain intact. Core-Three should be added as a separate versioned component/configuration, not achieved by changing `CONSENSUS_BOOKS` in place.

## 13. Focused implementation test plan

1. Exact three books succeed in canonical order; order of provider objects cannot affect output.
2. Each required book missing in turn rejects; no two-book result exists.
3. Extra or unknown book rejects.
4. Title alias, case variation, generic/global identity, and non-U.S. variant reject.
5. Duplicate bookmaker rejects, even if byte-identical.
6. Duplicate market key and conflicting same-key lines reject.
7. Alternate spread/total cannot substitute and unexpected alternate keys reject.
8. Suspended flag, null price, absent outcome, three-way h2h, malformed price/point, asymmetric spread, and mismatched total reject.
9. Missing, naïve, malformed, future, and older-than-ten-minute timestamps reject; explicit UTC/offset normalization is deterministic.
10. Tests keep freshness disabled/blocked until semantic approval is represented in versioned configuration.
11. Provider event ID, home/away, team mapping, or kickoff mismatch rejects; ambiguous mapping rejects.
12. Exact `00:15Z` versus `00:20Z` fixture rejects with `KICKOFF_MISMATCH`.
13. Postponed event cannot capture; reschedule appends revision and invalidates old window; post-acceptance change appends void without deletion or recapture; cancellation is terminal without win/loss.
14. Core-Three no-vig equal mean matches fixed fixtures and is invariant to input ordering; every book has exactly one-third weight.
15. DraftKings execution prices equal the same atomic h2h object; separate/later prices reject.
16. Raw bytes are not written when retention permission is absent; normalized provenance contains no credential.
17. Preview, rejected attempts, dry runs, and tests cannot touch real Core-Three evidence paths.
18. No capture is accepted before governance approval and effective timestamp.
19. Regression tests prove every original Step 91C–91I constant, fixture, and artifact remains unchanged.

## 14. Final readiness gates

| # | Gate | Status | Evidence | Blocking? | Resolution |
|---:|---|---|---|---|---|
| 1 | Core-Three identity | PASS | Distinct draft protocol, candidate-variant, evidence labels | Yes | Freeze later; no action now |
| 2 | Provider mappings | PARTIAL | Exact keys live-tested; jurisdiction not proven | Yes | Written feed classification and adapter tests |
| 3 | Market contract | PASS | Deterministic exact three-market rules and two-event conformance | Yes | Implement and audit |
| 4 | Consensus definition | PASS | No-vig equal three-book mean defined | Yes | Independent mathematical/implementation audit |
| 5 | Atomic capture | PASS design | One completed event response; no assembly | Yes | Implement timeout/retry and adapter |
| 6 | Event identity | PARTIAL | Exact contract defined; Provider A mapping absent | Yes | Implement mapping and prove uniqueness |
| 7 | Kickoff authority | FAIL | Step 91H official claim conflicts with Step 91I NFLVerse source | Yes | Official acquisition/hash/revalidation contract |
| 8 | Kickoff discrepancy | FAIL | Official/retained 00:20Z versus provider 00:15Z | Yes | Provider correction or documented deterministic resolution |
| 9 | Rescheduling | PARTIAL | Append-only rules specified; schemas absent | Yes | Implement and audit lifecycle events |
| 10 | Timestamps | UNKNOWN | ISO field exists; update trigger undocumented | Yes | Written provider semantics |
| 11 | Freshness | PARTIAL | Arithmetic defined; semantic input unapproved | Yes | Close timestamp gate and test |
| 12 | Jurisdiction | PARTIAL | Aggregate U.S. only; bookmaker filter precedence weakens proof | Yes | Written state/feed evidence and governance choice |
| 13 | DraftKings execution state | UNKNOWN | Same object is possible; state executability unproven | Yes | Name state and obtain objective equivalence evidence |
| 14 | Raw retention | UNKNOWN | Terms do not affirm required archival/review rights | Yes | Written permission or approved reduced provenance |
| 15 | Missing/stale/conflict | PASS design | Complete fail-closed table | Yes | Implement and adversarially test |
| 16 | Implementation | FAIL | Only original seven-book runtime exists | Yes | Build separate Core-Three components |
| 17 | Testing | FAIL | Test plan exists; implementation tests do not | Yes | Implement full plan and regressions |
| 18 | Effective timestamp | FAIL | No active protocol | Yes | Record externally after all prior gates pass |
| 19 | Governance approval | FAIL | Specification is draft only | Yes | Independent review and explicit freeze decision |
| 20 | Paid-provider requirement | PASS | Core-Three conformed under free entitlement | No | Monitor entitlement; no purchase required |

Classification: **BLOCKED ON PROVIDER, BLOCKED ON GOVERNANCE, AND BLOCKED ON ENGINEERING.** The draft is ready to guide implementation planning, but production implementation should not be represented as activation-ready until provider and governance gates close.

## 15. Original-protocol separation

Core-Three is not a repair, amendment, equivalent version, or continuation of the seven-book experiment. No seven-book observation or evidence may be relabeled, pooled, backfilled, or used as Core-Three evidence. The original protocol and its historical artifacts remain immutable and closed.

## Final safety report

- Money spent: **$0**
- Plan purchased: **NO**
- Prospective evidence: **0**
- Manifest: **untouched**
- Ledger: **untouched**
- Candidate: **unchanged**
- Coefficients: **unchanged**
- Thresholds: **unchanged**
- Residual cap: **unchanged**
- Execution venue: **unchanged**
- Original seven-book protocol: **unchanged**
- API requests: **0**
- Credits used: **0**
- Events tested: **0 new**; Phase 2B's two non-evidence events were referenced.

Stop after Phase 2C. Do not implement, freeze, activate, initialize prospective artifacts, or purchase provider access.
