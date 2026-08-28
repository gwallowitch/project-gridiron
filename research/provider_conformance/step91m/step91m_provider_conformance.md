# STEP 91M — Provider Conformance and Protocol Specification Closure

**NON-EVIDENCE PROVIDER CONFORMANCE DATA**

## 1. Executive summary

**NOT READY TO FREEZE OR IMPLEMENT.** A non-evidence The Odds API test returned structurally conforming 2026 NFL moneyline, featured spread, and featured total markets for BetMGM, FanDuel, and DraftKings. Caesars is officially mapped as paid-only `williamhill_us` but returned no rows under the present entitlement. The Odds API has no listed U.S. Bet365 key and returned no Bet365 rows.

Bet365 is **PARTIAL**, not failed: it is operational in the U.S., and Odds-API.io publicly distinguishes generic `Bet365` from `bet365 NJ`, but the available Odds-API.io credential returned HTTP 401. OpticOdds was not credentialed. Jurisdiction, timestamp semantics, and raw-retention rights remain unresolved.

## 2. Baseline verification

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- HEAD: `3f623d129a807c5c0868dc1b486e0311f87f85c7`
- Initial tree: clean
- Frozen candidate inspected and unchanged.
- No prices were retained or used.

## 3. Provider A — The Odds API

Documentation identifies NFL as `americanfootball_nfl`; U.S. region `us`; markets `h2h`, `spreads`, and `totals`; and keys `betmgm`, `fanduel`, `williamhill_us` (Caesars, paid only), and `draftkings`. No U.S. Bet365 key is listed.

On 2026-08-28 one authenticated non-evidence request returned HTTP 200 and 272 upcoming NFL event records. Sample structural record: event `8c94552d022acec4a0458d70c19d3da9`, New England Patriots at Seattle Seahawks, kickoff `2026-09-10T00:15:00Z`.

| Key | Rows | Markets | Finding |
|---|---:|---|---|
| `betmgm` | 16 | h2h, spreads, totals | PARTIAL: structure passes |
| `fanduel` | 32 | h2h, spreads, totals | PARTIAL: structure passes |
| `draftkings` | 272 | h2h, spreads, totals | PARTIAL: structure passes |
| `williamhill_us` | 0 | none | PARTIAL: paid catalog identity; entitled live test missing |
| `bet365` | 0 | none | FAIL as a verified Provider A U.S. source |

The main request cost three credits. Empty targeted checks returned HTTP 200; emptiness does not establish sportsbook nonexistence. The documented bookmaker `last_update` field does not unambiguously establish underlying quote-change versus provider-ingestion semantics.

Sources: https://the-odds-api.com/liveapi/guides/v4/ ; https://the-odds-api.com/sports-odds-data/bookmaker-apis.html ; https://the-odds-api.com/sports-odds-data/update-intervals.html

## 4. Provider B — Odds-API.io

The environment credential produced HTTP 401 (`You need to provide a valid apiKey`) for an NFL events request; no odds request was possible. Public documentation advertises all five books and required NFL markets. Its U.S. directory includes the Core Four, while its full catalog distinguishes generic `Bet365` from `bet365 NJ`; generic Bet365 is therefore not proven U.S. The market field `updatedAt` exists, but exact clock semantics remain unclear.

Result: **PARTIAL documentation; FAIL current authentication.** It cannot be activated or serve as backup.

Sources: https://docs.odds-api.io/authentication ; https://docs.odds-api.io/api-reference/odds/get-event-odds ; https://odds-api.io/sports/nfl ; https://odds-api.io/sportsbooks/us ; https://odds-api.io/sportsbooks

## 5. Provider C — OpticOdds

No credential was present. Documentation supports fixture IDs, sportsbook filters, odds timestamps, separate last-polled timestamps, and `is_main` filtering in historical views. Odds timestamps change when price or points change; last-polled represents provider polling and is not interchangeable. Historical data has rolling two-month retention, with timeseries requiring separate permission.

Result: **PARTIAL documented capability; authenticated identity, jurisdiction, entitlement, and customer-retention rights UNKNOWN.**

Sources: https://developer.opticodds.com/docs/odds-api-getting-started-guide ; https://developer.opticodds.com/reference/get_sportsbooks-last-polled ; https://developer.opticodds.com/reference/get_fixtures-odds-historical

## 6. Bet365 decision

**BET365: PARTIAL**

It is operational in 18 U.S. states, including Illinois. It has not passed equivalent provider conformance: no authenticated provider returned a verified regional U.S. NFL record with all three markets, usable timestamps, and understood retention rights. Generic `Bet365` must not substitute for an authenticated regional identity. Provider uncertainty is not sportsbook nonexistence.

Source: https://www.bet365.com/hub/en-us/states

## 7. Core Four matrix

| Book | Operational | U.S. jurisdiction | Provider A | Provider B | Provider C | ML/spread/total | Timestamp | Retention | Overall |
|---|---|---|---|---|---|---|---|---|---|
| BetMGM | PASS | PARTIAL | PARTIAL | PARTIAL docs / FAIL auth | UNKNOWN | PASS A structure | PARTIAL | UNKNOWN | PARTIAL |
| FanDuel | PASS | PARTIAL | PARTIAL | PARTIAL docs / FAIL auth | UNKNOWN | PASS A structure | PARTIAL | UNKNOWN | PARTIAL |
| Caesars | PASS | PARTIAL | PARTIAL paid | PARTIAL docs / FAIL auth | UNKNOWN | PARTIAL | PARTIAL | UNKNOWN | PARTIAL |
| DraftKings | PASS | PARTIAL | PARTIAL | PARTIAL docs / FAIL auth | UNKNOWN | PASS A structure | PARTIAL | UNKNOWN | PARTIAL |

## 8. Jurisdiction and identity mapping

| Book | Provider key | Feed | Limitation |
|---|---|---|---|
| BetMGM | `betmgm` | Provider A `us` | State represented is undocumented |
| FanDuel | `fanduel` | Provider A `us` | State represented is undocumented |
| Caesars | `williamhill_us` | Provider A `us` | Paid; state represented is undocumented |
| DraftKings | `draftkings` | Provider A `us` | Equivalence to execution state unresolved |
| Bet365 | Provider B `bet365 NJ` candidate | New Jersey-labelled | Catalog only; exact authenticated behavior unresolved |

“Canonical U.S. feed” must mean **provider-classified aggregate U.S. region**, not a presumed state-executable feed. Exact, case-sensitive identifiers must be used; title aliases, international variants, and duplicate canonical identities reject.

## 9. Timestamp semantics

| Provider | Field | Meaning | Status for freshness |
|---|---|---|---|
| The Odds API | `last_update` | Bookmaker record update; underlying event unclear | PARTIAL |
| Odds-API.io | `updatedAt` | Market update; polling/change distinction unclear | PARTIAL |
| OpticOdds | odds `timestamp` | Price or points last changed | PARTIAL pending authentication |
| OpticOdds | last-polled | Latest successful sportsbook poll | Liveness only |
| Collector | `receipt_at` | Local time after full response | PASS for local chronology only |

Minimum deterministic rule: the frozen provider timestamp must exist, be timezone-aware, be no later than `receipt_at`, and be at most ten minutes old. Missing or future timestamps reject. Any nonzero clock tolerance must be separately frozen; none is invented here.

## 10. Market and line conformance

1. Accept only `h2h`, `spreads`, and `totals` from one event-scoped response.
2. NFL h2h requires exactly two outcomes matched by canonical team identity; three-way or extra outcomes reject.
3. Spread requires exactly one complete home/away pair with opposite points.
4. Total requires exactly one Over/Under pair with identical points.
5. Null, missing, suspended, locked, nonnumeric, or incomplete prices are missing.
6. Alternate-market keys never substitute.
7. Exact duplicates may collapse; conflicting duplicates or multiple line pairs reject.
8. Spread and total remain contextual and do not gate moneyline consensus.

These rules eliminate operator line selection. Written confirmation that Provider A featured spread/total values are main lines remains desirable.

## 11. Fallback architecture

A second provider is **not necessary** for scientific validity. Recommended v1 architecture:

- Primary: The Odds API, only after all gates pass.
- Backup: none.
- Provider failure or invalid response: reject the capture attempt.
- No cross-provider or cross-call assembly.
- Never switch based on price, freshness advantage, edge, or model effect.

If a backup is added later, that is a protocol revision requiring frozen timeout, retry count, failure codes, provider priority, mappings, timestamp semantics, and disagreement behavior. Timeout and retry values remain unresolved rather than invented.

## 12. Raw retention

All three providers are **UNKNOWN** for the complete requested rights. The Odds API prohibits raw-data resale/repackaging/redistribution and directs uncertain users to contact it, but does not clearly grant indefinite storage or Git publication.

Written confirmation must cover internal storage, hashing, season retention, independent review, publication, Git inclusion, and post-subscription retention. If raw retention is prohibited, a canonical extract, request/response metadata, provider response ID, and response hash may be proposed for separate governance approval; it is not approved automatically. This is not legal advice.

Source: https://the-odds-api.com/terms-and-conditions.html

## 13. Cost and credit analysis

**POTENTIALLY NEEDED now; REQUIRED only if Core Four through Provider A is frozen.** Caesars is paid-only; Bet365 is unavailable from Provider A regardless of current free/paid evidence.

Conservative ceiling:

- Weeks 1–16: at most 256 games × 3 credits = 768.
- Two retries for every game: 1,536.
- 18 discovery calls: 18.
- Settlement score ceiling: 256 × 2 = 512.
- Conformance/schedule reserve: 200.
- Total: **3,034 credits**, below 20,000.

No plan was purchased.

## 14. Step 91L MUST-FIX closure

| Item | Status | Result |
|---|---|---|
| Bet365 | UNRESOLVED | Regional authenticated test needed |
| Objective universe rule | UNRESOLVED | Proposed: retain every surviving original book passing identical gates |
| Jurisdiction | UNRESOLVED | Aggregate `us` known; execution state unmatched |
| Raw retention | UNRESOLVED | Written permission needed |
| Primary provider | UNRESOLVED | Provider A conditional; Caesars not tested entitled |
| Backup provider | RESOLVED | None for v1 |
| Fallback trigger | RESOLVED | No fallback; failure rejects |
| Identity mapping | PARTIALLY RESOLVED | Core Four keys fixed; Bet365 unresolved |
| Timestamp semantics | UNRESOLVED | Fields known; authoritative meaning incomplete |
| Freshness rule | RESOLVED conceptually | Required timestamp, chronology, <=10 minutes |
| Main-line definition | RESOLVED | Exactly one complete featured pair; otherwise reject |
| Suspended behavior | RESOLVED | Treat as missing |
| Duplicate behavior | RESOLVED | Exact collapse; conflict rejects |
| Atomic capture | RESOLVED | One event response; no assembly |
| Kickoff authority | UNRESOLVED | Authority and moved-game lifecycle needed |
| DraftKings consistency | PARTIALLY RESOLVED | Same response for consensus/execution; state unresolved |
| Distinct identity | RESOLVED | New transportability candidate/protocol/evidence label required |
| Licensing gate | RESOLVED | Mandatory before activation |
| Post-implementation audit | RESOLVED | Mandatory before effective timestamp |

## 15. Remaining questions and recommendation

Unresolved: authenticated regional Bet365; paid Caesars live coverage; execution-state equivalence; exact Provider A timestamp meaning; retention rights; kickoff authority and moved-game handling; justified timeout/retry values.

**Next step:** obtain written Provider A answers on timestamp, state/feed meaning, Caesars entitlement, and retention; repair or replace the Provider B credential and test the regional Bet365 identity; then conduct a Step 91N freeze-readiness review applying identical gates to all surviving original books.

Do not freeze or implement. No historical ROI, P&L, candidate performance, or 2026 outcome informed this work.
