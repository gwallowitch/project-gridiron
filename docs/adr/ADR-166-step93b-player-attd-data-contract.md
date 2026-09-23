# ADR-166: Step 93B player anytime-TD data contract

## Status

Accepted as an offline, pre-acquisition evidence contract.

## Motivation and boundary

Step 93A classified player anytime-touchdown research as partially ready. The
provider documents `americanfootball_nfl` / `player_anytime_td`, event-specific
historical requests, and additional-market history beginning 2023-05-03, but
does not establish complete-board behavior, exact DraftKings/FanDuel/BetMGM
coverage, stable player IDs, universal Yes/No prices, player suspension/removal
behavior, retention permission, or deterministic GSIS resolution.

**STEP 93B MAKES ZERO PROVIDER REQUESTS.**

**STEP 93B CONSUMES ZERO API CREDITS.**

**STEP 93B DOES NOT FIT A PLAYER-TD MODEL.**

**STEP 93B DOES NOT CLAIM PLAYER-TD BETTING IS PROFITABLE.**

**STEP 93B DOES NOT AUTHORIZE BULK HISTORICAL ACQUISITION.**

**STEP 93B DOES NOT USE 2026 OUTCOMES.**

**STEP 93B DOES NOT MODIFY THE FROZEN SPREAD LANE.**

**STEP 93B DOES NOT MODIFY THE FROZEN MONEYLINE CANDIDATE.**

## Market, price, board, and book contracts

The sole target market is `player_anytime_td`; first, last, totals, and
multi-touchdown markets are not substitutes. Initial books use exact provider
keys `draftkings`, `fanduel`, and `betmgm`. Unknown books may be retained in
raw evidence but cannot satisfy the initial three-book research scope.

American prices are integers no closer to zero than -100 or +100. Decimal and
fractional formats are never silently converted. Raw break-even conversion is
descriptive market math, not fair probability or vig removal. Yes and No are
independent. Boards preserve counts and explicit missing, empty, ambiguous,
malformed, or unverified states. Structural validity never proves provider
board completeness, and multiple target-market instances fail closed.

## Identity and touchdown taxonomy

Canonical games retain provider event ID plus season, type, week, teams,
kickoff, and existing nflverse-compatible game identity. Event matching never
uses outcomes. GSIS ID is the preferred player identity. Raw and normalized
names, suffix, team, candidates, resolution method, and provenance are kept.
Fuzzy candidates cannot create authority; ambiguity and conflicts fail closed.

Football touchdown categories are rushing, receiving, kickoff return, punt
return, offensive or defensive fumble recovery, interception return, other
defensive return, other, and unknown. A passing touchdown is not itself a QB
scorer event. Extra points and two-point conversions are not touchdowns.
Football events remain separate from book-specific settlement.

## Settlement and participation

Rules are versioned by sportsbook, jurisdiction, effective dates, participation,
overtime, qualifying categories, inactive/no-snap behavior, abandonment,
postponement, corrections, source, review date, and authority. Current BetMGM
semantics remain unknown rather than inferred from obsolete rules.

Football participation is independently one of inactive, active-no-play,
participated, or unknown. Settlement is win, loss, void, push, or unresolved.
Unresolved event/player identity, participation, or rule authority produces an
unresolved result rather than an invented loss.

## Outcomes, corrections, and feature timing

Outcome evidence retains dataset/release, raw SHA-256, game/player/play,
touchdown category, period/overtime, observation time, correction version, and
predecessor provenance. Corrections create attributable versions and do not
silently overwrite labels.

Every future feature must satisfy
`feature_observed_at <= prediction_cutoff_at < kickoff_at`. Target-game realized
usage is prohibited. Prior-game sources may be lagged only after availability.
Unknown timing cannot become verified pregame evidence.

Personnel evidence preserves source/version/hash, observed/effective times,
injury, practice, game, roster, depth, and active states plus authority. It
does not transform designations into weights. Defensive and offensive evidence
may later support prior snaps, availability, replacements, competition, and
opportunity shares, but creates no causal or touchdown adjustment here.

## Raw provider artifact contract

Future samples preserve exact response bytes and SHA-256 plus provider,
sample item, event, requested/returned snapshot, acquisition time, HTTP status,
byte count, market, books, region, and odds format. API keys, authorization
headers, cookies, secret-bearing URLs, and environment dumps are prohibited.
The parser is offline and credential-free.

## Minimal future sample protocol

The frozen algorithm selects the first regular-season game by scheduled UTC
kickoff then canonical game ID for each of 2023, 2024, and 2025, from an
approved outcome-free schedule authority. It requests T12H and T1H for exactly
one market, one US region, American odds, and the three named books. Purpose is
only `SCHEMA_AND_COVERAGE_VALIDATION`.

Maximum requests: **6**. At the documented planning assumption of 10 credits
per event/market/region snapshot, the maximum estimate is **60 credits**.

Exact items are not materialized in Step 93B. The frozen Step 92F local schedule
authority covers 2021, 2023, and 2025; 2021 predates the documented player-prop
archive and it contains no 2024 authority. Substituting 2021 or deriving 2024
from an outcome-bearing report would violate the protocol. A later authorized
step must supply or approve an outcome-free 2024 schedule authority before
materialization and must obtain explicit human approval before any request.

## Sample audit

The later audit must report market/book presence, board/player counts, Yes/No
structure, duplicates, multiple markets, player IDs and team metadata,
suspension/removal representation, book and provider timestamps, quote age,
snapshot lag, price validity, GSIS resolution, cross-book union/intersection,
season schema differences, retention permission, and whether coverage supports
further consideration. It sets no predictive-quality or arbitrary board-size
threshold.

Readiness states range from `ATTD_SAMPLE_NOT_ACQUIRED` through acquired,
partial, schema-valid, coverage-insufficient, identity-insufficient,
settlement-unresolved, and failed. These are data-readiness states only.

A successful six-request sample does not authorize bulk acquisition, model
fitting, ROI analysis, threshold selection, or a betting recommendation.
Bulk acquisition requires a separate human decision after sample quality,
coverage, identity, economics, injury feasibility, and provider terms are
reviewed.

Step 92F remains frozen at manifest SHA-256
`e45976ed4768335095d3f6298a039c40a9ec1edb82361dddc11064e9ed8d464d`.
Step 92G remains unauthorized. The frozen moneyline candidate
`market-plus-def-epa-capped-0425-v1` and its coefficients, cap, books,
thresholds, ledger, and operational runner remain unchanged.
