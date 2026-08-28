# STEP 91O — Phase 2 Paid Provider / Conformance Verification

**NON-PROSPECTIVE / NON-EVIDENCE — PRE-PURCHASE STOP**

## Decision

The Odds API **20K plan at $30/month USD** is genuinely required and materially useful if governance retains the mandatory Core-Four universe with The Odds API as sole provider. The current entitlement does not return Caesars, and the official catalog marks `williamhill_us` as paid-only.

No purchase was made. Phase 2 stops at the mandatory pre-purchase boundary. The protocol remains unfrozen, unimplemented, and inactive.

## Baseline

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting HEAD: `3856d41ba93df114ba920b3cf8709ccd29c030f3`
- Starting tree: clean
- Candidate numbers, threshold, eligibility, consensus, and DraftKings execution are unchanged.

## Non-evidence request

Two Provider A calls were made on 2026-08-28:

1. Upcoming NFL event discovery: HTTP 200, zero credits.
2. One event-scoped odds request for `betmgm,fanduel,draftkings,williamhill_us` and `h2h,spreads,totals`: HTTP 200, three credits.

Classification: `NON-PROSPECTIVE / NON-EVIDENCE PROVIDER CONFORMANCE`.

Event metadata retained in this report:

- Provider event ID: `8c94552d022acec4a0458d70c19d3da9`
- Event: New England Patriots at Seattle Seahawks
- Scheduled kickoff: `2026-09-10T00:15:00Z`

No prices or raw response were retained. No credential was displayed or written.

## Structural findings

| Provider key | Objects | ML | Spread | Total | Outcomes structurally complete | Duplicated | Status |
|---|---:|---|---|---|---|---|---|
| `betmgm` | 1 | Yes | Yes | Yes | Yes | No | PASS |
| `fanduel` | 1 | Yes | Yes | Yes | Yes | No | PASS |
| `draftkings` | 1 | Yes | Yes | Yes | Yes | No | PASS |
| `williamhill_us` | 0 | No result | No result | No result | Not testable | No | FAIL under current entitlement |

The three returned books each had exactly two outcomes for every requested market. Moneylines contained the two named teams, spreads contained the two named teams with points, and totals contained Over and Under with points. Source identifiers were present for each outcome. No null price structure or duplicate bookmaker object was observed. Prices themselves were not recorded.

This establishes that the event-scoped response can structurally support atomic collection for three books. It does not establish full Core-Four atomic conformance because Caesars was absent.

## Commercial finding

Official Provider A evidence:

- Free plan: 500 credits/month, most bookmakers.
- 20K plan: $30/month USD, 20,000 credits/month, all bookmakers, all markets, and historical access.
- `williamhill_us` is mapped to Caesars in region `us` and is available only on paid subscriptions.
- Event odds for three markets and one region cost three credits.
- Event discovery does not count against quota.

Sources:

- https://the-odds-api.com/
- https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
- https://the-odds-api.com/liveapi/guides/v4/

### Exact plan required

`20K` — `$30/month USD` — `20,000 credits/month`.

This is the minimum published plan that claims all-bookmaker access. Billing is immediate and automatically recurs monthly until cancelled according to the provider's published FAQ.

### Credit sufficiency

The Phase 1 conservative operating estimate was 3,000 credits. This Phase 2 test used three credits. Even a doubled 6,000-credit contingency is well below 20,000. The plan is comfortably sufficient for the proposed request pattern; no higher plan is justified.

### Gates materially advanced by purchase

Paid access would permit, but would not itself prove:

- Caesars exact live identity under `williamhill_us`.
- Caesars upcoming NFL availability.
- Caesars moneyline, featured spread, and featured total structure.
- Caesars inclusion without duplicate identity in the same atomic event response.
- Market-level timestamp presence for Caesars.
- Commercial entitlement for the chosen provider architecture.

### Gates payment would not resolve

- Bet365: Provider A has no legitimate U.S. Bet365 catalog key.
- Exact state jurisdiction behind Provider A's aggregate `us` feed.
- DraftKings equivalence to the user's executable state/account price.
- Meaning of `last_update` beyond a market update field.
- Raw-response archival and independent-review permission.
- Official NFL kickoff authority and append-only rescheduling behavior.
- Suspended-market representation unless a suspended example or written specification is obtained.
- Governance approval, implementation audit, or effective timestamp.

## Gate table

| Gate | Status | Exact reason | Evidence needed | Would payment resolve? | Engineering? | Governance? |
|---|---|---|---|---|---|---|
| Bet365 disposition | PARTIAL | Operational U.S. book, but no authenticated qualifying regional feed | Regional U.S. provider identity, NFL markets, timestamps, retention | No | No | Yes after evidence |
| U.S. jurisdiction/execution state | PARTIAL | Provider documents aggregate `us`, not a state | Written state/feed explanation and named execution state | No | No | Yes |
| Caesars paid conformance | FAIL currently | Current entitlement returned zero `williamhill_us` objects | Paid one-event non-evidence test | **Enables test** | No | Yes after test |
| NFL coverage | PARTIAL | Three books pass; Caesars untested | Paid Caesars NFL response | **Enables resolution** | No | Yes |
| ML/spread/total conformance | PARTIAL | Three books pass; Caesars absent | Complete paid Caesars three-market response | **Enables resolution** | No | Yes |
| Provider timestamp semantics | UNKNOWN | Docs place `last_update` at market level but do not define update trigger | Written provider definition: trigger, clock, unchanged-quote behavior | No | No | Yes |
| Suspended-market representation | PARTIAL | Fail-closed policy exists; provider encoding not documented | Written schema or controlled non-evidence suspended case | Not necessarily | Parser later | Yes |
| Kickoff authority compatibility | PARTIAL | Provider event ID/commence time reconcile structurally; official source remains separate | Retained official NFL artifact and deterministic equality/outage rules | No | Later | Yes |
| Rescheduling behavior | PARTIAL | Append-only policy direction exists but no audited void representation | Frozen append-only void/reschedule contract | No | Later | Yes |
| DraftKings execution-state equivalence | UNKNOWN | Aggregate Provider A quote is not proven executable in a named state/account | Named execution state plus provider/book evidence | No | No | Yes |
| Raw-response retention | UNKNOWN | Terms restrict redistribution but do not affirm requested archival rights | Written permission for normalized data, hashes, raw retention, review, and post-subscription handling | No | No | Yes |
| Commercial entitlement | FAIL currently | Existing key lacks paid-only Caesars | User-authorized 20K purchase and paid conformance | **Yes** | No | Yes |

## Timestamp finding

For the event-odds endpoint, Provider A documents `last_update` at market level rather than bookmaker level because markets update on their own schedules. That establishes location and granularity, not semantics. Documentation does not say whether it is sportsbook price-change time, provider observation time, polling time, or publication time, nor what happens when a quote is unchanged.

The ten-minute freshness gate therefore remains `UNKNOWN`. Written clarification is required before `last_update` can be assigned to protocol `quote_at`.

## Retention finding

Provider terms prohibit resale, repackaging, or redistribution as a standalone raw-data product and direct uncertain users to contact the provider. They do not expressly grant the intended internal raw archival, season retention, hashing, independent-review access, publication, Git inclusion, or post-subscription retention.

Status: `UNKNOWN`. Payment does not cure this ambiguity. No raw response was retained in Phase 2.

Source: https://the-odds-api.com/terms-and-conditions.html

## Pre-purchase requirements

Before the user confirms purchase:

1. Accept that the plan advances only Caesars and commercial conformance, not all freeze gates.
2. Obtain or request written Provider A clarification for `last_update`, feed/state meaning, and retention rights.
3. Define the exact sanitized paid Caesars test and success criteria.
4. Confirm that Bet365 requires a separate provider decision and is not supplied by this purchase.
5. Confirm immediate recurring billing and cancellation responsibility.

After purchase, the only authorized live work should be one minimal non-evidence Caesars/Core-Four event test. It must not create a manifest, ledger entry, candidate calculation, wager, or prospective observation.

## Stop decision

**STOP BEFORE PURCHASE.**

- Recommended plan if user confirms: The Odds API 20K.
- Price: $30/month USD.
- Expected use: approximately 3,000 credits under the conservative protocol model.
- Money spent in this task: $0.
- Plan purchased: no.
- Subscription activated: no.
- Credits used in this task: 3.
- API calls made: 2.
- Prospective evidence: 0.
- Real manifest: untouched/uninitialized.
- Real ledger: untouched/empty.
- Frozen candidate: unchanged.
- Protocol: not frozen, not implemented, not activated.

The purchase is necessary and materially useful for a Core-Four Provider A design, but insufficient to make that design freeze-ready by itself.
