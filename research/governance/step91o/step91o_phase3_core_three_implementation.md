# STEP 91O — Phase 3 Core-Three Implementation

**CORE-THREE — IMPLEMENTATION — NON-PROSPECTIVE**

## Result

**Does the implemented architecture support the proposed Core-Three protocol deterministically? PARTIAL.**

The new, separate architecture deterministically implements exact bookmaker identity, the complete three-market contract, one-response normalization, zero-tolerance event/kickoff reconciliation, timestamp parsing and freshness arithmetic, equal one-third no-vig consensus, same-object DraftKings execution representation, append-only lifecycle transitions, raw non-retention, and a non-evidence preview boundary.

It is intentionally inactive. It refuses timestamp-dependent normalization unless a test-only semantic approval is explicit, exposes no network collector, real manifest, real ledger, settlement, or evidence-writing command, and cannot close external provider/governance facts. It must not be described as activation-ready.

## Baseline and separation

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`
- Branch: `feature/step91i-prospective-collection-operations`
- Starting local and remote HEAD: `04b44f171117a38df6734b070253a2fd04ce4517`
- Starting tree: clean
- Original Step 91C–91I implementation: closed, unchanged, and protected by byte-hash regression tests.
- Prior governance artifacts: unchanged.
- Live provider access: not used.

## Implementation summary

### Inactive configuration

`config/step91o_core_three_protocol_v1.json` freezes the separate draft identity, immutable candidate numbers, exact `betmgm/fanduel/draftkings` universe, `h2h/spreads/totals` markets, one-third consensus, all-three completeness, one-response boundary, 55–65-minute window, ten-minute arithmetic, zero kickoff tolerance, raw non-retention, unresolved external gates, `activation_allowed=false`, and zero evidence.

### Provider and market normalization

`core_three_provider.py` validates exactly one event response:

- Exact provider event ID, home team, away team, and authoritative kickoff.
- Receipt inside the frozen window.
- Exactly the three canonical keys; aliases, case variants, generic/regional variants, extras, missing and duplicate bookmakers reject.
- Exactly one h2h, spread, and total per book.
- Two canonical outcomes, valid American odds, opposite spread points, equal total points.
- Alternate, duplicate, conflicting, suspended, malformed, incomplete, and three-way structures reject.
- Explicit timezone, UTC normalization, no future timestamps, and at most ten-minute arithmetic.
- Timestamp semantics must be explicitly approved; default behavior rejects.
- No raw payload persistence.

### Consensus and DraftKings

`core_three_consensus.py` reuses the protocol-neutral two-sided vig-removal utility and computes the arithmetic mean of BetMGM, FanDuel, and DraftKings home probabilities, exactly one-third each. It retains the immutable coefficients in preview metadata without recalibration.

DraftKings execution prices are derived from the identical validated atomic h2h object. The output explicitly states that execution-state equivalence is unresolved; no provider quote is represented as proof of state/account executability.

### Lifecycle and evidence boundary

`core_three_lifecycle.py` provides a pure in-memory SHA-256 append-only chain for scheduled, accepted/rejected capture status, postponement, pre-acceptance schedule revision, post-acceptance decision void, and cancellation. It never mutates prior events and prevents reaccepting an already accepted game.

`core_three_operations.py` and `scripts/step91o_core_three.py` expose only sanitized, offline, non-prospective preview behavior. They do not initialize or write a manifest, ledger, raw archive, settlement, or evidence. The CLI's timestamp approval switch is explicitly synthetic/test-only and output remains inactive/non-evidence.

## Files created

- `config/step91o_core_three_protocol_v1.json`
- `src/gridiron/market/core_three_types.py`
- `src/gridiron/market/core_three_provider.py`
- `src/gridiron/market/core_three_consensus.py`
- `src/gridiron/market/core_three_lifecycle.py`
- `src/gridiron/market/core_three_operations.py`
- `scripts/step91o_core_three.py`
- `tests/test_core_three_provider.py`
- `tests/test_core_three_consensus.py`
- `tests/test_core_three_lifecycle.py`
- `tests/test_core_three_operations.py`
- `tests/test_core_three_frozen_separation.py`
- `research/governance/step91o/step91o_phase3_core_three_implementation.md`
- `research/governance/step91o/step91o_phase3_core_three_implementation.json`

Files modified: none. All implementation files are new and separately named.

## Adversarial coverage

The 48 focused tests cover:

- Exact BetMGM, FanDuel, DraftKings acceptance and canonical ordering.
- Each missing book; aliases; generic, extra, and regional keys; duplicate bookmaker.
- Each missing market; duplicate and alternate market keys.
- Suspended, missing outcome, null/invalid price, three-way h2h, conflicting spread and total.
- Event ID, home, away, mixed-event, and kickoff mismatches, including 00:15Z versus 00:20Z.
- Stale, future, naïve, invalid, and offset timestamps; unresolved semantic gate.
- One-third no-vig consensus, order invariance, missing-book refusal, no seven-book denominator.
- Same-object DraftKings execution and explicit unresolved state.
- Postponement, reschedule, cancellation, accepted-decision void, immutable acceptance, and chain tampering.
- Inactive config, sanitized preview, default gate refusal, preview-only CLI, no raw/manifest/ledger/evidence writes.
- Selected frozen Step 91C–91I file hashes.

The focused suite passed 48/48. A combined run with 140 relevant existing Step 91C–91I tests passed 188/188. Compilation passed.

## Frozen-file audit

`git status` contains only new Core-Three and Phase 3 files. No frozen config, module, script, test, schedule, evidence, manifest, or ledger is modified. The separation test verifies baseline SHA-256 values for representative critical Step 91C, 91D, 91H, and 91I configurations and ledger, ingestion, integrity, and operations modules. Existing regression tests also preserve seven-book identity, completeness, aliases, latest-selection behavior, raw retention, lifecycle, audit, and evidence behavior exactly as frozen.

## Remaining external gates

1. Provider `last_update` semantics: exact update trigger and unchanged-quote behavior remain unknown.
2. Jurisdiction: aggregate `us` does not prove a named state.
3. DraftKings execution-state equivalence: provider data does not prove account/state executability.
4. Raw-retention permission: internal archival, review, publication, and post-subscription rights remain unresolved.
5. Authoritative kickoff: official artifact acquisition/revalidation is not approved; Provider A's 00:15Z conflict remains.
6. Timeout/retry operational values: not prospectively frozen.
7. Governance approval and independent implementation audit: not completed.
8. Effective timestamp: absent by design.
9. Real evidence paths and activation command: deliberately not implemented.

No identified gate was resolved by invention or test-only flags.

## Validation

- Core-Three focused tests: 48 passed.
- Relevant frozen Step 91C–91I regression tests: 140 passed.
- Combined run: 188 passed.
- JSON validation: passed.
- Python compilation: passed.
- Credential scan: passed.
- Whitespace and Git diff checks: passed.
- Ruff: unavailable; no package was installed.
- Live API requests: 0; credits used: 0; events tested: 0.

## Safety audit

- Money spent: **$0**
- Provider plan purchased: **NO**
- Caesars activated: **NO**
- Prospective evidence: **0**
- Manifest: **untouched**
- Ledger: **untouched**
- Original seven-book protocol: **unchanged**
- Candidate: **unchanged**
- Coefficients: **unchanged**
- Thresholds: **unchanged**
- Residual cap: **unchanged**
- Execution venue: **unchanged**

Stop after Phase 3. Core-Three remains unfrozen and inactive.
