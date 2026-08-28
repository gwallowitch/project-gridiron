# STEP 91N — Core-Four Protocol Governance Closure

**GOVERNANCE / NON-PROSPECTIVE**

## Decision

**Original seven-book experiment: CLOSED / TERMINATED FOR 2026 PROSPECTIVE COLLECTION.**

**Proposed Core-Four experiment: DRAFT CONDITIONALLY APPROVED, NOT FREEZE-READY, UNIMPLEMENTED, AND UNACTIVATED.**

The original seven-book protocol cannot produce a valid 2026 observation because SI Sportsbook and U.S. Betway no longer represent legitimate current U.S. sportsbook identities. The original protocol remains historically frozen and is not amended.

The proposed Core-Four design is a new transportability experiment. Its observations may never be pooled with, substituted for, or represented as continuation of the original seven-book experiment. No prospective evidence has been collected under either protocol. No 2026 outcome data or historical performance informed this governance decision.

## Baseline and evidence boundary

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Starting branch: `feature/step91i-prospective-collection-operations`
- Starting SHA: `7afb2850d72749916160f6698bce8a5d366681f0`
- Starting tree: clean
- Step 91M artifacts were read and not modified.
- Step 91M provider activity remains `NON-EVIDENCE PROVIDER CONFORMANCE DATA`.
- This document is governance only. It is not a protocol configuration, manifest, ledger event, capture, decision, or evidence artifact.

## Experiment identities

- Design label: `step91k-2026-live-market-core-four-v1`
- Status: `DESIGN_LABEL_ONLY`
- Candidate label: `market-plus-def-epa-capped-0425-v1 / step91k-core-four transportability variant`
- Evidence class if later activated: `REAL PROSPECTIVE DATA — STEP91K CORE-FOUR V1`
- Original protocol status: `CLOSED_FOR_2026_OPERATIONAL_INFEASIBILITY`

The coefficients, intercept, 4.25% residual cap, strict-positive-edge rule, DraftKings execution venue, 2026 regular-season Weeks 1–16 eligibility, 55–65-minute window, and ten-minute maximum quote age remain numerically unchanged. Because the market feature changes from a seven-book mean to a four-book mean, the resulting system is not mathematically equivalent to the original candidate.

## Objective sportsbook-universe rule

A sportsbook is eligible only if every condition below is established before the protocol freeze:

1. It is a surviving identity from the original seven-book universe.
2. It is a currently operational, regulated U.S. sportsbook.
3. It offers NFL moneyline, main spread, and main total markets.
4. A selected provider exposes an exact, stable sportsbook identifier in a verifiable U.S. feed.
5. Provider timestamp semantics support the frozen chronology and freshness rules.
6. The required normalized fields and audit provenance are reproducible without operator judgment.
7. Licensing permits the approved retention and independent-audit structure.
8. Any required commercial entitlement passes a non-evidence conformance test.

The rule applies equally and does not select books based on access convenience, price, ROI, model output, or expected performance.

| Original book | Operational identity? | Eligible now? | Governance reason |
|---|---|---|---|
| Bet365 | Yes, U.S. operations confirmed | **UNRESOLVED** | Survives original universe, but no authenticated regional provider passed all conformance and retention gates |
| SI Sportsbook | No | No | Obsolete identity |
| U.S. Betway | No | No | Obsolete U.S. identity |
| BetMGM | Yes | Conditional | Provider A structure passed; jurisdiction, timestamp, retention gates remain |
| FanDuel | Yes | Conditional | Provider A structure passed; jurisdiction, timestamp, retention gates remain |
| Caesars | Yes | Conditional | Exact paid-only Provider A key exists; paid conformance, timestamp, jurisdiction, retention remain |
| DraftKings | Yes | Conditional | Provider A structure passed; execution-state equivalence, timestamp, retention remain |

Fanatics, Hard Rock, theScore Bet, and other successors or replacement books are not selected because condition 1 limits v1 to surviving original identities. Adding any would require a separately governed replacement-universe protocol.

## Bet365 disposition

**Status: UNRESOLVED; excluded from the Core-Four draft, but not finally declared ineligible.**

Bet365 is operational in the United States. Provider A has no verified U.S. Bet365 identifier. Provider B publicly distinguishes generic `Bet365` from a regional `bet365 NJ` identity, but the available credential failed authentication, so NFL markets and timestamps were not verified. Provider C was documentation-only. Retention permission is unknown.

The draft excludes Bet365 because it has not yet passed the same objective sourcing, jurisdiction, timestamp, reproducibility, and licensing gates applied to every book—not because of its prices or performance. Final freeze is prohibited until Bet365 either passes and the universe is reconsidered or fails documented equal conformance criteria and is formally excluded.

## Draft v1 provider architecture

**PRIMARY PROVIDER ONLY — NO BACKUP PROVIDER**

| Book | Provider | Identifier | Feed | Event identifier | Markets | Role |
|---|---|---|---|---|---|---|
| BetMGM | The Odds API | `betmgm` | `us` | Provider `americanfootball_nfl` event `id` | `h2h`, `spreads`, `totals` | Primary |
| FanDuel | The Odds API | `fanduel` | `us` | Same provider event `id` | `h2h`, `spreads`, `totals` | Primary |
| Caesars | The Odds API | `williamhill_us` | `us` | Same provider event `id` | `h2h`, `spreads`, `totals` | Primary, paid entitlement required |
| DraftKings | The Odds API | `draftkings` | `us` | Same provider event `id` | `h2h`, `spreads`, `totals` | Primary and execution |

No provider substitution or cross-provider assembly is allowed. Provider failure produces a rejected attempt. A backup can be introduced only in a future protocol revision that freezes its identity, jurisdiction, priority, trigger, timeout, retry, timestamp, and conflict behavior before collection.

## U.S. jurisdiction contract

For the draft, U.S. means the selected provider's explicitly classified aggregate U.S. feed, `regions=us`, combined with the exact canonical identifier above. It does not mean that a brand name alone proves jurisdiction or that the returned line is executable in every state.

The collector must reject:

- Global, international, UK, EU, AU, or other regional variants.
- Unqualified aliases not in the frozen mapping.
- A sportsbook returned under multiple unresolved identities.
- A provider response whose region cannot be established.

This item remains a hard pre-activation gate because Provider A documentation does not establish the exact state represented. The DraftKings execution jurisdiction must be named, and equivalence between its executable price and the provider observation must be verified or the executable price must be separately captured under a frozen rule.

## Timestamp and freshness contract

- `quote_at`: the selected provider timestamp attached to the bookmaker/market observation, once its semantics are confirmed.
- `receipt_at`: trusted local UTC timestamp recorded after the complete response body is received and before parsing-dependent decisions.
- `quote_age`: `receipt_at - quote_at`.
- Qualifying capture: `receipt_at` is 55–65 minutes before the authoritative scheduled kickoff.
- Required: `quote_at <= receipt_at` and `quote_age <= 10 minutes` for every consensus book.
- Missing timestamp: reject.
- Future timestamp: reject.
- Outside window: reject.
- HTTP latency: retain for operational audit only; it is not an eligibility threshold.
- Clock tolerance: zero unless a different value is prospectively approved before freeze.

Provider written clarification of `last_update` semantics is a hard gate. No timestamp field may be assigned an invented meaning.

## Canonical markets

All fields must share the canonical provider event ID and canonical home/away team identities.

### Moneyline

- Provider market: `h2h`.
- Exactly two outcomes matching home and away teams.
- No draw or third outcome.
- Both prices numeric and available.
- Moneyline is the only model input.

### Main spread

- Provider market: featured `spreads`, never `alternate_spreads`.
- Exactly one complete home/away pair.
- Points must be equal and opposite.
- Multiple or conflicting pairs reject the contextual spread.

### Main total

- Provider market: featured `totals`, never `alternate_totals`.
- Exactly one Over/Under pair at the same total.
- Multiple or conflicting pairs reject the contextual total.

Suspended, locked, unavailable, null, missing, nonnumeric, or malformed outcomes are missing. No favorable-price or operator-selected line is allowed. Spread and total are contextual audit fields and do not gate a complete moneyline consensus.

## Moneyline consensus

For American odds `a`:

- If `a > 0`, implied probability is `100 / (a + 100)`.
- If `a < 0`, implied probability is `-a / (-a + 100)`.

For each book:

`p_home_book = implied_home / (implied_home + implied_away)`

Core-Four consensus:

`mean(p_home_BetMGM, p_home_FanDuel, p_home_Caesars, p_home_DraftKings)`

All four fresh two-sided moneylines are mandatory. One missing, stale, invalid, or conflicted book rejects the capture. Median, trimming, weighting, provider weighting, imputation, and three-of-four fallbacks are prohibited.

## DraftKings consensus and execution contract

DraftKings is both a 25% consensus constituent and the execution sportsbook. This dual role is explicit and inherited from the original design.

The DraftKings consensus odds and executable odds must derive from the same canonical bookmaker object in the same atomic provider response. No later or separately favorable price may replace it. If the selected side lacks a valid DraftKings price, the observation cannot become a bet. State-specific execution equivalence remains a hard gate.

## Duplicates and conflicts

- Exact duplicate: collapse only when provider, event, book, region, market, outcomes, points, prices, and timestamps all agree.
- Conflicting duplicate: reject the affected book and therefore reject consensus.
- Unknown identity: reject.
- Wrong jurisdiction: reject.
- Multiple canonical lines: reject; do not choose.
- Provider disagreement: not applicable in v1 because there is no backup.

## Atomic capture

All four books and all requested markets must come from one completed, event-scoped Provider A response. `receipt_at` applies to that complete response. No fields may be assembled from earlier calls, later calls, cached odds, or another provider.

A failed request may produce only a rejected attempt. Exact timeout, retry count, and target request time must be frozen in the implementation specification before activation; until then this gate is unresolved. No retry may occur outside the 55–65-minute window or after an accepted capture.

## Kickoff authority and lifecycle

The authoritative schedule source must be the official NFL schedule, with provider `commence_time` used only after equality to the authoritative value is verified. Schedule must be revalidated immediately before the capture request and again before accepting the response.

- Change detected before acceptance: use the new official kickoff and evaluate the window against it; a stale-window response rejects.
- Change detected after an accepted decision but before kickoff: mark the decision non-qualifying/void through an append-only governance event; do not silently retain it and do not recapture under v1.
- Postponed or rescheduled before capture: no capture until a new official kickoff exists and its proper window occurs.
- Cancelled: no qualifying decision; settlement classification is cancellation/zero under existing economics.

The exact official schedule retrieval artifact, hashing, outage behavior, and append-only void event must be specified and independently audited before activation. Therefore this gate remains unresolved despite the deterministic policy direction.

## Raw retention and licensing gate

Collection cannot activate without written provider confirmation addressing:

- Internal complete-response storage.
- Permitted retention duration and post-subscription deletion/retention.
- Hashing.
- Normalized derived records.
- Independent reviewer access.
- Publication or sharing.
- Git-repository inclusion.

If raw retention is not permitted, a proposed substitute using canonical extracted fields, sanitized request/response metadata, a provider response ID where available, and a response hash requires separate governance approval. Permission is not assumed, and this document is not legal advice.

## Commercial gate and ordered sequence

Do not purchase the plan until:

1. This governance design is accepted as a draft.
2. Bet365 receives a final equal-criteria disposition.
3. Provider jurisdiction, timestamp, and retention questions receive written answers.
4. The final protocol specification is approved.
5. Paid entitlement is authorized.
6. A limited paid, non-evidence Caesars conformance test passes.
7. Implementation is completed without changing the frozen scientific rules.
8. An independent implementation audit passes.
9. A prospective effective timestamp is recorded externally.
10. Only then may collection begin.

The estimated 3,034-credit conservative requirement fits within 20,000 credits, but no purchase is authorized here.

## Pre-activation gates

Every gate below is mandatory. Activation is prohibited while any gate is `FAIL` or `UNRESOLVED`.

| # | Gate | Status | Closure evidence |
|---:|---|---|---|
| 1 | Original seven-book closure | PASS | Formally closed here without amendment |
| 2 | New protocol identity | PASS | Distinct design and candidate-variant labels defined |
| 3 | Objective universe rule | PASS | Equal outcome-independent rule defined |
| 4 | Bet365 disposition | UNRESOLVED | Authenticated regional test or documented failure required |
| 5 | U.S. jurisdiction definition | UNRESOLVED | State/feed meaning and execution state must be verified |
| 6 | Provider identity mapping | PASS for draft | Exact Core-Four keys defined; must be live-verified under entitlement |
| 7 | NFL market conformance | UNRESOLVED | Caesars paid conformance missing |
| 8 | Timestamp semantics | UNRESOLVED | Written Provider A clarification required |
| 9 | Freshness rule | PASS | Chronology and ten-minute rule deterministic |
| 10 | Main-line definition | PASS | Exact featured-market rules defined |
| 11 | Duplicate behavior | PASS | Exact collapse; conflict rejects |
| 12 | Suspended behavior | PASS | Treated as missing |
| 13 | Atomic capture | PASS for design | One response/no assembly; timeout/retry implementation values unresolved |
| 14 | Kickoff authority | UNRESOLVED | Retrieval, hashing, outage handling not specified |
| 15 | Rescheduling behavior | UNRESOLVED | Append-only void mechanism requires specification/audit |
| 16 | DraftKings snapshot consistency | UNRESOLVED | Same snapshot defined; execution-state equivalence missing |
| 17 | Fallback behavior | PASS | No backup; provider failure rejects |
| 18 | Raw retention permission | UNRESOLVED | Written permission required |
| 19 | Commercial entitlement | UNRESOLVED | Purchase not authorized; paid test not performed |
| 20 | Independent implementation audit | UNRESOLVED | No implementation exists |
| 21 | Effective timestamp | UNRESOLVED | May be set only after all prior gates pass |

## Final governance conclusion

The original seven-book experiment is closed for 2026 collection. The Core-Four design is a scientifically distinct, outcome-independent transportability proposal, but it is **not freeze-ready**. It remains a design label only. No production configuration, manifest, ledger, evidence, effective timestamp, or active protocol is created by Step 91N.

The next authorized work should be external/provider clarification and regional Bet365 plus paid Caesars non-evidence conformance. A later governance review must resolve every remaining gate before implementation or activation.
