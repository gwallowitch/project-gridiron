# ADR-163: Step 92E historical spread acquisition protocol

## Status

Accepted as offline, non-prospective acquisition-readiness infrastructure.

## Context and decision

Step 92D classified the retained 2025 workbook as Category C: it is useful for
structural and descriptive work but lacks trustworthy observation timestamps,
formal open/close semantics, raw responses, provider event identities, immutable
provenance, and multi-season depth. That authority is unchanged.

The Odds API is the first conditional Category A acquisition candidate because
its documented archive exposes named books, point and price, UTC snapshots,
bookmaker updates, event identities, and commence times across multiple seasons.
These documented capabilities are not validated Project Gridiron evidence until
a separately authorized saved sample passes this protocol.

The blinded sample is fixed before acquisition: seasons 2021, 2023, and 2025;
regular-season Weeks 2, 8, and 15; the first two games ordered by scheduled UTC
kickoff then canonical game ID; plus the first Wild Card game under the same
ordering when available. No score or outcome may enter selection. The five
targets are T12H (720), T6H (360), T3H (180), T1H (60), and NEAR_KICKOFF (15)
minutes before kickoff. The maximum is 21 games and 105 requests.

Manifest generation is offline, deterministic, canonically serialized, and
hashed. It requires an outcome-free canonical schedule supplied by the caller;
the repository presently has no retained 2021/2023/2025 schedule authority.
Requests are limited to `americanfootball_nfl`, US `spreads`, American odds,
and DraftKings, FanDuel, and BetMGM.

## Evidence and audit semantics

Every future response must retain exact raw bytes, sanitized request metadata,
requested and returned timestamps, acquisition time, status, provider identity,
manifest item/hash, byte count, and SHA-256. Credentials, authorization headers,
secret-bearing URLs, and environment dumps are forbidden.

The parser is offline. It keeps historical archive lag separate from the Step
92B ten-minute live freshness rule. It records signed target lag and quote age,
rejects snapshots after target, quotes after snapshots or targets, and quotes at
or after kickoff. No observed lag tolerance is optimized or silently imposed.

Exactly one ordinary `spreads` market with exactly two team-mapped, opposing
points is required per book. Duplicate books, duplicate spread markets, or any
unresolved main/alternate ambiguity fail closed. It never selects by ordering,
price balance, consensus proximity, or eventual outcome.

Provider-returned American odds and the requested format are preserved. No
conversion is performed. A future decimal-odds protocol would require a separate
decision and versioned conversion method.

Coverage is reported separately for each Core-Three book and by season, game,
and target. Counts and lag distributions are data-quality statistics only. No
cover, ATS, profit, ROI, edge, calibration, or model-performance calculation is
present. With no acquired sample, readiness is
`HISTORICAL_SAMPLE_NOT_ACQUIRED`. Because no quantitative pass threshold has
been justified before inspection, parsed data defaults to
`HISTORICAL_SAMPLE_AUDIT_PARTIAL`; malformed or wholly unusable data fails.

Future result joins are a separate authority. Preferred identity is a shared
provider event ID; otherwise normalized home/away teams, UTC kickoff, season,
season type, and a controlled alias table are required. Relocations,
postponements, kickoff revisions, neutral sites, and international games must
be resolved explicitly. This layer neither fetches nor stores final scores.

The cost estimator is pure and accepts credits per request, plan allowance, and
plan price as caller-supplied assumptions. It does not encode a permanent plan
or make a provider request.

## Boundaries

**STEP 92E DOES NOT AUTHORIZE MODEL FITTING.**

**STEP 92E DOES NOT AUTHORIZE BULK HISTORICAL ACQUISITION.**

**STEP 92E DOES NOT AUTHORIZE 2026 OUTCOME USE.**

**STEP 92E DOES NOT CREATE FORMAL PROSPECTIVE EVIDENCE.**

**STEP 92E DOES NOT ACTIVATE SPREAD CLOUD COLLECTION.**

It also does not consume provider credits, access credentials, purchase a plan,
alter Step 92B/92C, write operational evidence, or change the frozen moneyline,
totals, prospective, cloud, or DEF EPA authorities.
