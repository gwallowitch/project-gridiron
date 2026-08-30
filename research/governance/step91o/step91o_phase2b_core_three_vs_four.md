# STEP 91O — Phase 2B Core-Three vs Core-Four Governance / Conformance

**PHASE 2B — FREE-ONLY — NON-PROSPECTIVE / NON-EVIDENCE**

## Recommendation

**CORE-THREE PREFERRED.**

For a prospective v1 design, BetMGM + FanDuel + DraftKings is the more defensible current proposal. Two free-entitlement event tests produced complete, deterministic three-book moneyline, featured-spread, and featured-total snapshots. Available evidence does not show that Caesars improves timestamps, jurisdiction, event identity, execution confidence, market coverage, or line granularity. Under the existing all-books-required, fail-closed philosophy, adding Caesars does not create failure tolerance: it adds another mandatory failure condition plus a paid dependency and unresolved conformance burden.

This is not a claim that three books are intrinsically better, that Caesars lacks informational value, or that fewer books improve model performance. It is a protocol-design conclusion based on demonstrated value versus demonstrated burden. Core-Three is a distinct proposed estimand and transportability experiment; it is **not frozen, implemented, or activated** by this recommendation.

## Baseline and evidence boundary

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting local and remote HEAD: `cac9ac9c53f5e4eb0e8634725fd78dcd75cbf5c8`
- Starting tree: clean
- Step 91M, Step 91N, Step 91O Phase 1, pre-purchase, and Phase 2A artifacts were read and not modified.
- No raw provider response was retained. Only the requested sanitized event, market, line, price, timestamp, and structure fields appear here.
- No outcome, model evaluation, optimization, recalibration, manifest, ledger, or prospective evidence was used.

## Free test design and accounting

Provider A was queried for two upcoming NFL events using region `us`, exact bookmaker keys `betmgm,fanduel,draftkings,williamhill_us`, markets `h2h,spreads,totals`, American prices, ISO timestamps, and source IDs.

- API requests: 4 total: two zero-credit discovery requests (the first response was discarded after a local quota-header conversion error) and two successful event-odds requests.
- Credits used: 6 total, three per event-odds request.
- Events tested: 2.
- Credits remaining after the test: 446.
- Money spent: $0.

### Event 1 — New England Patriots at Seattle Seahawks

- Provider event ID: `8c94552d022acec4a0458d70c19d3da9`
- Provider commence time: `2026-09-10T00:15:00Z`
- Receipt time: `2026-08-30T17:23:55.5712889Z`

| Book | Market | Last update | Outcomes with price/point |
|---|---|---|---|
| BetMGM | h2h | `2026-08-30T17:23:52Z` | New England +155; Seattle -190 |
| BetMGM | spreads | `2026-08-30T17:23:52Z` | New England +3.5/-108; Seattle -3.5/-110 |
| BetMGM | totals | `2026-08-30T17:23:52Z` | Over 44.5/-112; Under 44.5/-108 |
| FanDuel | h2h | `2026-08-30T17:23:18Z` | New England +164; Seattle -196 |
| FanDuel | spreads | `2026-08-30T17:23:18Z` | New England +3.5/-108; Seattle -3.5/-112 |
| FanDuel | totals | `2026-08-30T17:23:18Z` | Over 44.5/-110; Under 44.5/-110 |
| DraftKings | h2h | `2026-08-30T17:23:19Z` | New England +150; Seattle -180 |
| DraftKings | spreads | `2026-08-30T17:23:19Z` | New England +3.5/-115; Seattle -3.5/-105 |
| DraftKings | totals | `2026-08-30T17:23:19Z` | Over 44.5/-110; Under 44.5/-110 |

### Event 2 — San Francisco 49ers at Los Angeles Rams

- Provider event ID: `acc580d74344ea3b31bbcdd057fe6a9c`
- Provider commence time: `2026-09-11T00:35:00Z`
- Receipt time: `2026-08-30T17:23:55.7373013Z`

| Book | Market | Last update | Outcomes with price/point |
|---|---|---|---|
| BetMGM | h2h | `2026-08-30T17:23:52Z` | Los Angeles -190; San Francisco +155 |
| BetMGM | spreads | `2026-08-30T17:23:52Z` | Los Angeles -3.5/-108; San Francisco +3.5/-110 |
| BetMGM | totals | `2026-08-30T17:23:52Z` | Over 48.5/-110; Under 48.5/-108 |
| FanDuel | h2h | `2026-08-30T17:23:18Z` | Los Angeles -200; San Francisco +168 |
| FanDuel | spreads | `2026-08-30T17:23:18Z` | Los Angeles -3.5/-115; San Francisco +3.5/-105 |
| FanDuel | totals | `2026-08-30T17:23:18Z` | Over 48.5/-110; Under 48.5/-110 |
| DraftKings | h2h | `2026-08-30T17:23:19Z` | Los Angeles -185; San Francisco +154 |
| DraftKings | spreads | `2026-08-30T17:23:19Z` | Los Angeles -3.5/-105; San Francisco +3.5/-115 |
| DraftKings | totals | `2026-08-30T17:23:19Z` | Over 48.5/-108; Under 48.5/-112 |

Every returned book had one bookmaker object, exactly the three requested market keys, two outcomes per market, source IDs at bookmaker and outcome level, non-null numeric prices, opposite spread points, and matching total points. No alternate key, duplicate bookmaker, duplicate market, incomplete pair, explicit suspension field, deep link, or jurisdiction/state field was observed. Cross-book price differences are normal constituent variation, not conflicting duplicates.

Caesars `williamhill_us` returned zero objects in both responses: **PAID_REQUIRED**.

## Core-Three quality

Core-Three can produce a deterministic equal-weight consensus when all three two-sided moneylines pass. For each book, remove vig by normalizing home and away implied probabilities; then take the arithmetic mean of the three home probabilities. The two samples provided exactly one eligible input per book without operator selection.

Core-Three remains fail-closed:

- One missing, stale, malformed, suspended, conflicted, or wrong-jurisdiction book rejects the observation.
- Three-of-two, imputation, reweighting, cached replacement, cross-call assembly, and favorable-price selection are prohibited.
- Featured `h2h`, `spreads`, and `totals` keys are accepted; alternate keys do not substitute.
- A complete event-scoped response is the atomic boundary.

Timestamp fields were timezone-aware and mechanically permit `receipt_at - last_update`; observed ages were under one minute. That proves arithmetic and field availability only. It does not prove that `last_update` is sportsbook odds-change time. Freshness semantics remain **UNKNOWN** pending provider documentation.

Provider mapping is structurally deterministic for `betmgm`, `fanduel`, and `draftkings`. Region `us` remains aggregate provider classification, not state proof. DraftKings source IDs do not prove that its price equals an executable price for a named state/account. Execution-state equivalence remains **UNKNOWN**.

## Kickoff discrepancy

Current official evidence supports `2026-09-10T00:20:00Z` for Patriots at Seahawks:

- NFL Week 1 lists Wednesday, September 9 at 8:20 p.m. ET: https://www.nfl.com/schedules/2026/by-week/week-1
- The Seahawks schedule lists 5:20 p.m. PDT: https://www.seahawks.com/schedule/2026/
- The retained NFLVerse row also says `00:20Z`.

Provider A continued to return `00:15Z` on August 30. The five-minute difference is not a timezone conversion: both official local times convert to `00:20Z`. No reviewed evidence identifies a legitimate schedule revision to `00:15Z`. Provider staleness or data error is plausible but not proven. Classification: **UNKNOWN cause / FAIL strict reconciliation**. Kickoff authority is unchanged, and this event would reject under an exact-equality rule.

The second event reconciled: Provider A and the retained schedule both reported `2026-09-11T00:35:00Z`. One match does not resolve the authority and rescheduling lifecycle gates.

## Caesars incremental-value analysis

### A. Information diversity

Caesars would be a fourth named sportsbook and could add a distinct observed price. Free evidence cannot establish its live fields, pricing independence, correlation with the other books, or incremental information quality. A brand identity alone does not establish statistical independence. Status: **UNKNOWN**.

### B. Robustness and failure tolerance

With all books mandatory, neither design tolerates a missing constituent. Core-Three rejects when any of three fails; Core-Four rejects when any of four fails. The fourth book therefore does not provide redundancy under the frozen fail-closed rule. It increases the number of required successful validations. True one-book tolerance would require changing the missingness and weighting rules, which is not authorized. Core-Three: **PASS design clarity**; Core-Four incremental resilience: **FAIL**.

### C. Data quality

No evidence shows that Caesars provides better timestamps, market coverage, line granularity, event identity, jurisdiction information, or execution-state evidence. Its live NFL structure is unavailable without payment. Status: **PAID_REQUIRED for conformance; UNKNOWN for superiority**.

### D. Operational complexity

Both proposals use one Provider A response, so neither adds a second feed. Core-Four nevertheless adds a canonical mapping, mandatory object and three-market validation, timestamp/freshness checks, missing/suspension/conflict paths, retention scope, conformance evidence, and a paid entitlement. Atomic capture remains possible in principle for either, but only Core-Three has been observed complete. Core-Four adds implementation and operational failure surface without observed compensating functionality.

### E. Cost

Core-Three is accessible under the current free entitlement. Caesars requires Provider A paid access; the known minimum is approximately $30/month for the 20K plan. No purchase was made. Cost alone is not dispositive, but payment is an incremental burden tied to an unproven incremental benefit.

## Protocol distinction

Removing or adding Caesars changes the estimand:

- Core-Three gives each constituent weight `1/3`.
- Core-Four gives each constituent weight `1/4`.
- Required-book missingness changes from three mandatory validations to four.
- Every constituent must independently pass the same timestamp and freshness gates.
- The sampled game population can differ because any required-book failure rejects the game.

Core-Three cannot be described as the same protocol with one optional book removed. It needs a distinct protocol/candidate-variant identity, frozen universe, specification, effective timestamp, implementation, and independent audit. Coefficients and thresholds were not changed here.

## Comparison table

| Dimension | Core-Three | Core-Four |
|---|---|---|
| Books | 3 | 4 |
| BetMGM | PASS | PASS |
| FanDuel | PASS | PASS |
| DraftKings | PASS | PASS |
| Caesars | Not included | PAID_REQUIRED |
| Paid access | PASS: not required for tested books | PAID_REQUIRED |
| Provider complexity | PARTIAL: adapter still needed | PARTIAL: adapter plus paid Caesars validation |
| Atomic capture | PASS in two provider samples; engineering pending | PARTIAL: designed, not observed complete |
| Market completeness | PASS in two samples | PARTIAL: three books pass, Caesars untested |
| Timestamp coverage | PASS field presence; semantics UNKNOWN | PARTIAL: Caesars presence and all semantics unresolved |
| Jurisdiction confidence | PARTIAL: aggregate `us` only | PARTIAL: no demonstrated improvement |
| Execution confidence | UNKNOWN | UNKNOWN |
| Failure tolerance | FAIL: one missing book rejects | FAIL: one missing book rejects; extra failure surface |
| Scientific defensibility | PARTIAL: deterministic, but external gates remain | PARTIAL: distinct estimand plus unproven marginal value |

## Bet365 and DraftKings

Bet365 does not decide Core-Three versus Core-Four. It remains a surviving original identity with unresolved authenticated U.S. provider conformance; it is neither included nor classified obsolete. Adding it would create another distinct universe decision.

DraftKings being both a Core-Three constituent and execution venue preserves same-snapshot identity and gives it one-third rather than one-quarter consensus weight. That is a transparent estimand change, not evidence of an advantage. Provider DraftKings still is not proven equal to executable DraftKings in a named state/account. Status: **UNKNOWN** for execution equivalence in both designs.

## Implementation review

No production code was changed. A new implementation is required for either proposal because the frozen Step 91C–91I architecture hard-codes the original seven books and protocol identity. Core-Three specifically requires:

1. A distinct protocol/candidate-variant identifier and exact three-key mapping.
2. A Provider A event adapter retaining region, event ID, exact key, markets, source IDs, timestamps, and receipt metadata under approved retention rules.
3. Exact-key canonicalization instead of permissive title aliases.
4. One-response atomic validation with conflict rejection, not latest-observation selection across calls.
5. Featured spread/total normalization alongside the moneyline input.
6. Fail-closed three-book completeness and timezone-aware freshness validation after timestamp semantics are documented.
7. Official kickoff reconciliation and append-only reschedule/void behavior.
8. State-specific DraftKings execution-equivalence evidence.
9. A retention design that does not write raw provider data before licensing approval.

Existing append-only integrity, hashing, window, numeric validation, and DraftKings separation concepts can be reused only through separately governed implementation work. The original seven-book code remains unchanged.

## Why a paid test is not required for this recommendation

A paid call could establish Caesars live structural conformance. It could not, by itself, establish that a four-book mean is more valid than a three-book mean, that Caesars is statistically independent, that it improves state or timestamp semantics, or that it increases failure tolerance under an all-books-required rule. The demonstrated Core-Three structure is sufficient to prefer the simpler proposed design unless governance first identifies a specific, testable methodological benefit that only Caesars can supply.

## Final safety report

- Money spent: **$0**
- Plan purchased: **NO**
- Subscription activated: **NO**
- Prospective evidence: **0**
- Manifest: **untouched**
- Ledger: **untouched**
- Candidate: **unchanged**
- Coefficients: **unchanged**
- Thresholds: **unchanged**
- Residual cap: **unchanged**
- Execution venue: **unchanged**
- Original seven-book protocol: **unchanged**
- API requests: **4**
- Credits used: **6**
- Events tested: **2**

Stop after Phase 2B. Do not purchase Caesars access, freeze either proposal, activate collection, or initialize prospective artifacts.
