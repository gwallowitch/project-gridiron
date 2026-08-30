# STEP 91O — PHASE 4A — 2025 HISTORICAL DATA AVAILABILITY AND LOOK-AHEAD AUDIT

2025 HISTORICAL RESEARCH — NON-PROSPECTIVE — NON-EVIDENCE

## Decision

**NO-GO for an exact, leakage-safe frozen-candidate replay or a true historical Core-Three replay using the repository as it stands.** Some components are available for limited data-quality and feature-logic research; that is not a full replay.

The repository contains all 272 regular-season game identities and recorded scores, sportsbook-labelled historical prices, and game-indexed prior-week DEF EPA features. It does **not** establish historical market observation times, authoritative kickoff times/revisions, exact historical feed/state identities, same-response atomicity, or the publication/version history of the EPA inputs. Numerical availability is not point-in-time provenance. No performance replay, candidate prediction, economic evaluation, or optimization was run in Phase 4A.

## Baseline, scope, and method

- Repository: `C:\Users\grego\Desktop\ProjectGridiron\project-gridiron-codex`.
- Branch: `feature/step91i-prospective-collection-operations`.
- Starting SHA: `9ad202922ecb9da90df6470dbef4a0ff75e66a96`.
- `HEAD` and `origin/feature/step91i-prospective-collection-operations` matched; initial porcelain status was empty. This verifies the requested remote-tracking ref, not a fresh server fetch.
- Read both Markdown and JSON for Step 91M, Step 91N, and Step 91O Phases 1, 2 pre-purchase, 2A, 2B, 2C, 2D, and 3. None was modified.
- Searched tracked and ignored files, including `data`, `database`, and `step90g_transfer`; inspected workbook values/metadata, Parquet schemas/rows/footer metadata, and DuckDB in read-only mode. Did not search unrelated repositories or obtain new sports data.
- The spreadsheets skill was used for read-only workbook inspection and source/derived-data separation. No workbook was edited, recalculated, or exported.
- DuckDB 1.5.5 and Polars 1.44.1 were installed into an isolated temporary directory outside the repository to enable data inspection and tests. Native-library access required approved elevated execution. Python was bundled 3.12.13, not the project's declared 3.13 runtime. No dependency or environment file in the repository changed. No Ruff installation was attempted.
- All paths below are repository-relative unless stated otherwise. The companion JSON records structured details and source hashes.

## Historical inventory

| Source | Format / size | Coverage and granularity | Relevant fields | Temporal resolution and provenance | Classification |
|---|---|---|---|---|---|
| `step90g_transfer/nfl2025_complete_validation.xlsx`, sheet `NFL 2025`, `A1:CJ286` | XLSX; 285 data rows, 88 columns; 142,133 bytes | 272 REG games plus 13 postseason; REG dates 2025-09-04 through 2026-01-04 | Week/day/date, full team names; ESPN probabilities/ML/spread/total; opener ML/spread/total; seven named books' two-sided ML, spread points/prices, total line/Over/Under prices; scores/winner/Notes | Game date only. No kickoff, quote time, receipt time, provider event/key, state, source URL or response hash. Workbook creation 2026-03-17 19:42:00 and modification 20:05:17, timezone unspecified; these are post-season file metadata, not quote times | Mixed retrospective market/result table; market pre-game status UNKNOWN; scores POST-GAME |
| `step90g_transfer/recent_form_features_2025.parquet` | Parquet; 285 rows, 45 columns; 81,133 bytes | One row per game; season 2025, weeks 1–22. REG membership obtained by identity join to predictions | Game ID/season/week/teams; home/away season-to-date and recent EPA, success, counts, known flags, trends; `def_epa_trend_advantage` | Prior-week feature indexing. No acquisition/publication/as-of timestamp, source hash, raw play IDs, or EPA model version. Footer says Polars; only `ARROW:schema` key-value metadata | AVAILABLE WITH TEMPORAL LIMITATION; intended PRE-GAME aggregate, actual historical availability UNKNOWN |
| `step90g_transfer/predictions_2025.parquet` | Parquet; 285 rows, 18 columns; 21,872 bytes | Season 2025, weeks 1–22, dates 2025-09-04 through 2026-02-08; 272 REG / 13 postseason | Game ID/type/day/teams, rating week, PGR/HFA/difference, expected margin, home/away probability, predicted winner/confidence, model version | Game date and rating week, no prediction timestamp/kickoff. All rows model `v2`; not the frozen market-plus-DEF-EPA candidate. Footer says Polars; no temporal provenance beyond schema | Identity source and legacy derived predictions; not substitute frozen predictions |
| `database/gridiron.duckdb` | DuckDB; 798,720 bytes | One table `ingestion_log`, one row: schedules season 2026 | Run/dataset/season/row and column counts/path/imported_at/status/pipeline version/error | Logs 2026 schedule import at 2026-08-27 17:11:17.425065; no 2025 records, scores, EPA, or sportsbook tables | NOT A 2025 DATA ARCHIVE |
| `data/reports/backtests/backtest_2025_v1.{md,json}` and `backtest_2025_v2.{md,json}` | Markdown/JSON aggregate reports | Legacy v1/v2 retrospective evaluation; reports say 284 evaluated games | Aggregate performance/calibration, model version, counts | Not game-level inputs or time-stamped predictions. The 284 count is not proof of a missing REG game: transfer data has 285 total games and one tie, but the exact report exclusion is not independently reproduced here | POST-GAME summaries; not replay inputs |
| `data/reports/research/recent_form_validation_78b.{md,json}` and other feature/research validation reports under `data/reports/research/` | Markdown/JSON aggregate reports | Historical feature coverage/dispersion, including 2025; other reports cover feature experiments/calibration | Counts, distributions, aggregate diagnostics | No retained raw 2025 plays, weekly source versions, or market timestamps | Retrospective supporting documentation only |
| `docs/adr/ADR-137-feature-level-market-residual-research.md`, `ADR-138-bounded-def-epa-market-residual-correction.md`, `ADR-139-untouched-2025-def-epa-residual-validation.md`; `step90g_transfer/STEP90G_BUILD_PROMPT.md` | Markdown | Prior candidate selection, 2025 evaluation, transfer description | Feature name, fixed coefficients/cap, book universe, population, previous results | Research history, not an independent time-stamped input archive. Transfer files committed in `17529d576d0b8b22230c4ab15e31e118f870f310` on 2026-08-23 | Governance/provenance context, not new evidence |
| `data/raw/schedules/schedules_2026.parquet`, retained Step 91I schedule JSON and existing manifest JSONL; Step 91M–91O provider reports | Parquet/JSON/JSONL/Markdown | 2026 schedule and non-evidence provider checks only | Schedule metadata and a few 2026 conformance observations | Wrong season. Existing manifest contains SCHEDULED records, not historical market evidence | EXCLUDED; untouched |
| Expected `data/raw/schedules/schedules_2025.parquet`, `data/raw/play_by_play/play_by_play_2025.parquet`, `data/curated/...` 2025 source datasets and provider-response archives | Not found | No raw 2025 schedule/PBP, team-game source table, or dated market snapshot archive found | Required source rows/versions absent | Loader/pipeline code exists, but code is not stored historical data | UNAVAILABLE LOCALLY |

The workbook has no formulas, comments, hyperlinks, external workbook links, named ranges, hidden rows, or hidden columns providing additional provenance. Its `opener` labels do not establish an opening timestamp, and no column declares a closing timestamp. Do not call any unspecified book column a verified closing line. Config QB CSVs and synthetic test fixtures are not frozen-candidate inputs or historical observations.

## Game/result availability and quality

- Workbook REG rows: **272**, all with date, home/away team, nonnegative integer final scores and a non-null winner label. Each of 32 teams appears in 17 games. Weeks 1–16 contain **240** rows, ending 2025-12-22; Weeks 17–18 contain 32 rows and remain outside the frozen core population.
- Prediction and feature files each have **285 unique game IDs**, with no duplicate IDs and no missing cross-file IDs. Prediction `game_type` explicitly separates 272 REG from 6 WC, 4 DIV, 2 CON and 1 SB. Feature rows alone lack game type; never infer REG merely from season.
- All 272 workbook REG rows join one-to-one by week and exact home/away orientation to prediction IDs using a one-to-one 32-team audit mapping. No unmatched games or date disagreements. No duplicate workbook week/away/home keys, missing REG dates/teams/scores, invalid score values, day/date disagreements, or future game dates relative to this audit were found.
- This establishes **internal coverage**, not independent official score verification. The workbook is the only retained game-level final-score source found. Conflicts with an external official result source cannot be tested locally.
- **Tie error:** sheet row 63, `2025_04_GB_DAL`, scores 40–40, but `winner` says Green Bay Packers. A tie cannot be converted into an away win. Preserve the source, flag the discrepancy, and derive any later result only under the approved tie policy.
- **Name inconsistency:** row 178, `2025_12_TB_LA`, scores 7–34, winner `L.A. Rams` rather than the home label `Los Angeles Rams`. This is an outcome-label alias, not a demonstrated score conflict. Explicit canonicalization is needed.
- **Book-label change:** row 196 Notes says `Draftkings Odds (ESPN retired)`. ESPN fields cannot be assumed to represent a stable distinct book throughout the file; the note's exact extent is undocumented. Original SI/Betway labels likewise do not authenticate a 2025 operator/feed. Do not silently map successor identities.
- Postponement, cancellation, flexing and rescheduling history: **UNKNOWN**. No revision timestamps, original/revised kickoffs, or authority history exist locally. A final date match does not prove absence of schedule changes.
- Authoritative time-of-day kickoff and pre-game cutoff: **UNAVAILABLE** for every historical game inspected. Calendar dates are insufficient for 55–65-minute capture or ten-minute quote-age checks.

## DEF EPA: exact feature and leakage boundary

The candidate expects **`def_epa_trend_advantage`**, not generic team defensive EPA or a full-season defensive ranking. Evidence: ADR-139 and `src/gridiron/features/recent_form/features.py`.

The source pipeline `src/gridiron/pipelines/recent_form_features.py` loads a retained schedule and calls `NFLVerseGateway.play_by_play`, which delegates to `nflreadpy.load_pbp`. It writes derived features but does not retain the raw PBP in this pipeline. The inspected checkout has no raw 2025 PBP or 2025 ingestion-log entry linking the transfer file to an acquisition/version.

The current builder:

1. Includes run/pass plays with non-null offense/defense teams and usable EPA.
2. Groups by season, week and defensive team to compute mean offensive EPA allowed per eligible play.
3. For a target week `w`, includes only history with `week_history < w` in the same season.
4. Takes an **unweighted mean of weekly means** for season-to-date EPA allowed, not a play-count-weighted whole-season average.
5. Takes the same kind of mean for weeks `w-3` through `w-1`; this is three calendar weeks, not necessarily three games when a team has a bye.
6. Computes each team's improvement as season-to-date mean minus recent mean, then home improvement minus away improvement.

`d = (home_season_def_epa_allowed - home_recent_def_epa_allowed) - (away_season_def_epa_allowed - away_recent_def_epa_allowed)`.

Stored-data checks: no formula discrepancies above `1e-12` among non-null rows; no non-finite float values; all 16 null DEF EPA values are in Week 1; no later-week nulls. All 544 REG team-game history-depth checks match prior scheduled weeks and the prior-three-calendar-week window. These are useful consistency checks, not proof of original source publication times.

| Target | Permitted history | Stored example | Audit result |
|---|---|---|---|
| Week 1 | No 2025 games | `2025_01_DAL_PHI`: zero prior weeks; feature null | Frozen missing-Week-1 rule supplies 0.0; no future-season substitution |
| Week 5 | Weeks 1–4; recent 2–4 | `2025_05_SF_LA`: 4 prior weeks each; 3 recent each | Stored feature 0.04898474380671393; aggregate identity consistent |
| Week 10 | Weeks 1–9; recent 7–9 | `2025_10_LV_DEN`: home 9 / away 8 prior weeks; 3 / 2 recent | Stored feature 0.02314292572539428; bye-aware counts consistent |
| Week 18 | Weeks 1–17; recent 15–17 | `2025_18_NO_ATL`: 16 prior games each; 3 recent each | Stored feature -0.07893516389910415; audit example only, not frozen-core eligibility |

Four in-memory synthetic tests replaced all target-week and future EPA values with extreme values for Weeks 1, 5, 10 and 18. Each target's complete feature row remained unchanged. Existing recent-form tests also passed. Thus **current-code week exclusion PASS; historical source-vintage proof UNKNOWN**.

The data is **not final-season-only**. It supports inspection of cumulative/prior-week features. Nevertheless a regenerated PBP file may include later scoring corrections or an EPA model/version unavailable at the target cutoff. Week numbers also cannot prove a postponed prior-week game had actually finished before a target game. Missing raw rows, publication/ingestion timestamps and model/version provenance prevent certifying exact as-known-at-the-time values. Full DEF EPA reconstruction is blocked on that provenance, not on an observed use of final-season averages. Never replace the feature with final-season EPA, a weighted average, a last-three-games average, or inferred raw plays.

## Historical market and Core-Three availability

| Book | Stored range, REG rows 2–273 | Numerical coverage | Exact historical provider identity | Timestamp / jurisdiction / provenance | Decision |
|---|---|---|---|---|---|
| BetMGM | `AW:BE` | 272 two-sided MLs plus spread/total fields; no nulls | Book-labelled columns only; no authenticated provider key/event ID | UNKNOWN / UNKNOWN / undocumented original capture | Not a conformed historical observation |
| FanDuel | `BF:BN` | Same 272-game coverage | Same limitation | UNKNOWN / UNKNOWN / undocumented original capture | Not a conformed historical observation |
| DraftKings | `BX:CF` | Same 272-game coverage; intended execution prices present numerically | Same limitation; no account/state executable-price proof | UNKNOWN / UNKNOWN / undocumented original capture | Not a conformed historical execution snapshot |

Current Provider A keys documented in prior governance (`betmgm`, `fanduel`, `draftkings`) cannot be retroactively assigned to these spreadsheet columns. Those reports concern 2026 conformance, not the origin of the 2025 prices. There is no response envelope proving all books/markets were simultaneous or collected together.

All seven named books have 272 non-null, finite, integer two-sided ML pairs with absolute American price at least 100. Equal-weight no-vig arithmetic is mechanically possible, but no consensus performance or candidate probability was calculated. The workbook contains no stored consensus or synchronized historical snapshot proof. No other book, generic market, current response, or reconstructed price may replace missing provenance.

Additional spread-quality failures, using exact `away_spread == -home_spread`:

- BetMGM: **15** rows, all in Weeks 4–5.
- FanDuel: **30** rows, all in Weeks 4–5 (sheet rows 50–79).
- DraftKings: **30** rows, all in Weeks 4–5 (rows 50–79).
- Caesars: **23** rows in Weeks 4–5; separate `PK` strings occur in three pairs and require an explicit parsing rule, not numeric coercion by guess.
- Betway: **1**, row 239 (`2025_16_LV_HOU`), both sides +13.5.
- Bet365 and SI: zero non-opposite numeric pairs found.

The JSON lists every affected row. In total 99 book-game spread pairs fail, across 31 games; the Core-Three union is 30 games. Causes are unknown; possible transcription or asynchronous lines must not be treated as proven causes. All three markets are mandatory in the new Core-Three specification, so complete ML alone would not make those rows conform. A single total-line column also does not prove separately captured Over/Under point identity. No sides were repaired or copied across books.

ESPN uses `EVEN` strings (existing moneyline parsing supports that spelling); this is not evidence of missing odds. No original quote times exist with which to test future/stale/impossible timestamps: those tests are **NOT TESTABLE**, not passed. The workbook's post-season modified date cannot be used as a pre-game receipt time.

**True historical Core-Three replay: cannot be constructed from the retained data.** Price columns exist; required temporal/identity/atomic provenance does not, and some market pairs fail structural rules.

## Frozen-candidate requirements and availability

| Required input or rule | Availability | Could contain post-cutoff information? | Resolution without invention |
|---|---|---|---|
| Game ID, season, REG/week, home/away orientation | AVAILABLE | Final schedule can hide revisions | Identity join works; require historical authority/version for timing |
| Historical official kickoff and schedule revisions | UNAVAILABLE | Yes, final schedules can be revised | Obtain authentic versioned schedule records; do not invent times |
| Decision/capture cutoff and quote/receipt timestamps | UNAVAILABLE | Yes; date-only lines could be later than intended cutoff | Authentic original snapshot metadata required |
| Seven exact original books' two-sided ML | AVAILABLE WITH TEMPORAL LIMITATION | Yes; snapshot time and historical identities unknown | Authenticate original source and times, no substitutions |
| Three-book variant ML/spread/total and atomic provenance | AVAILABLE WITH TEMPORAL LIMITATION for labelled prices; UNAVAILABLE for conforming snapshots | Yes; potentially different moments; malformed pairs | Recover authentic original records; otherwise no Core-Three replay |
| `def_epa_trend_advantage` | AVAILABLE WITH TEMPORAL LIMITATION | Yes, source revisions/model vintage/publication can postdate cutoff | Raw/versioned PBP and historical availability lineage required |
| Week 1 neutral value 0.0 | AVAILABLE as frozen rule | No future information required | Apply only to missing Week 1 feature; later-week missing rejects |
| Numeric coefficients, intercept, cap, side and positive-edge rule | AVAILABLE | Constants do not add later game information | Use exact fixed values; never call a fitting path |
| DraftKings two-sided execution prices | AVAILABLE WITH TEMPORAL LIMITATION | Yes; timing/state/executability unproven | Same-cutoff authenticated execution record required |
| Final scores and result | AVAILABLE WITH TEMPORAL LIMITATION | Necessarily post-game; acceptable for labels only | Keep physically/logically separate from feature construction; reconcile tie/name issue and verify scores |
| Retention rights and original source permissions | UNKNOWN | Not a statistical input but a provenance gate | Establish rights from original source; no assumed permission |
| Outcome-independent population/tie convention | AVAILABLE core REG Weeks 1–16; historical tie reconciliation UNKNOWN | An outcome-dependent change would bias evaluation | Resolve legacy discrepancy before any performance run |

Frozen arithmetic, sourced from `config/step91c_prospective_data_capture_v1.json` and `src/gridiron/market/prospective_ledger.py`:

- Candidate: `market-plus-def-epa-capped-0425-v1`.
- For each original book, normalize its two implied moneyline probabilities; let `m` be the arithmetic mean across all seven books, with no missing-book reweighting.
- `z = -2.514766 + 4.980172*m + 1.044827*d`.
- `q = 1 / (1 + exp(-z))`.
- `p_home = min(m + 0.0425, max(m - 0.0425, q))`; `p_away = 1 - p_home`.
- Select HOME if `p_home >= m`, otherwise AWAY. This is residual direction, not simply the more probable winner.
- Selected-side edge = candidate probability minus the implied break-even probability of the captured DraftKings price. Qualifies only if edge is strictly positive; no best-side/price search.

Three-book `m` is a distinct transportability feature, not an exact reproduction of the seven-book candidate. Historical analysis must retain that distinction.

Implementation caveat: `untouched_validation.run_frozen_untouched_validation` and `economic_validation.build_frozen_candidate_probabilities` actually fit models using supplied training data and cap against a fitted market-only baseline. They are not drop-in fixed-coefficient replay functions. The mandated fixed arithmetic above uses the frozen ledger's direct consensus baseline. Reproducing old Step 90E/F numerical reports exactly would additionally require their original training inputs, baseline parameters and full computation provenance; those are not established by the transfer files. Do not refit or silently conflate these paths.

ADR-138 excludes ties; ADR-139 describes 240 Week 1–16 games. The retained 240 include the mislabeled Week 4 tie, leaving 239 non-tied games by recorded scores. The frozen ledger represents PUSH separately, whereas the older binary historical record requires a winning team. This is a reconciliation gate for any comparison to old reports, not permission to alter eligibility or count the tie as a win. ADR-139 also declares 2025 **consumed validation data**: no future analysis may call it newly untouched.

## Timing model and conditional Phase 4B procedure

Prediction time must be an authenticated historical observation/capture cutoff, not the audit date, workbook modification time, game-date midnight, or a made-up kickoff-minus-one-hour timestamp. To claim fidelity to the prospective timing model, the archived receipt must be 55–65 minutes before historically authoritative kickoff and every required quote at most ten minutes old under approved timestamp semantics. No such timestamps were found. A verified closing snapshot could support a separately labelled closing-time historical study, but cannot be represented as an earlier snapshot; even closing status is unproven here.

If all prerequisites are later supplied and separately authorized, the outcome-blind procedure is:

1. Enumerate all 2025 REG identities, retain Weeks 1–16 as the frozen core, and log every exclusion/failure. Inventory Weeks 17–18 and postseason separately; do not expand the core.
2. Reconcile official game identity, orientation, historical kickoff/revisions and prediction cutoff from authentic source records. Block ambiguous identities/times.
3. Load only source data demonstrably published and available before that cutoff, retaining source versions/hashes. Keep scores/winner labels inaccessible to feature construction.
4. Construct exactly the prior-week, unweighted-weekly-mean DEF EPA trend described above, admitting only completed and available prior games. Apply only the frozen Week 1 missingness rule; any unavailable later-week value blocks that game.
5. Validate every required original book's two-sided ML, identity, timing and completeness, then compute the fixed seven-book no-vig mean. A separately approved Core-Three research variant must be labelled separately and satisfy its own nine-market contract; never silently swap denominators.
6. Apply the fixed coefficients and intercept directly, without training, then the symmetric 0.0425 probability cap about the correct consensus baseline.
7. Apply the frozen residual-direction side rule and strict-positive offered-price edge using the authenticated captured DraftKings odds. Retain no-bets and failures, not only favorable cases.
8. Record immutable historical-only prediction/cutoff/source-hash/rejection metadata outside all prospective paths. This plan does not create such files now.
9. Only after predictions are sealed, join verified actual final scores. Treat ties/cancellations under the pre-resolved rule; never trust the erroneous winner cell.
10. Classify win/loss/push/no-bet/unavailable and compute only predeclared diagnostics. Do not search thresholds, books, caps, edge bands or exclusions based on outcomes.
11. Reconcile sample counts and independently audit all source-to-cutoff joins before interpreting results.

Present recommended Phase 4B scope: **source-provenance recovery, score/tie/name reconciliation and historical feature-vintage validation only**. These may be useful limited analyses, but no full candidate replay, verified closing-line analysis, ATS claim, or economic conclusion is justified now. No external data acquisition is performed or authorized by this report.

## Metrics Phase 4B could define after the gates pass

- Prediction error: Brier score and log loss for non-tied binary outcomes, with denominators and any fixed numerical clipping convention declared in advance. No probability-to-point-margin conversion is supplied by this candidate.
- ATS win/push/loss rates: **not a native frozen-candidate metric**. This is a moneyline probability candidate, not a spread or margin model. Legacy v2 `expected_home_margin` is not a substitute. A separately approved spread-analysis rule and authentic spread snapshots would be needed; do not invent one here.
- Moneyline win/loss/push rates: report each with explicit denominators; separately report cancellations, no-bets, rejected data and total in-scope games. Never count ties as binary wins.
- Mean edge: mean selected-side offered-price edge over a predeclared population; distinguish all valid observations from qualifying bets.
- Flat-unit profit: a win returns `odds/100` for positive odds or `100/abs(odds)` for negative odds; loss -1; push/cancellation 0 under the approved settlement convention. ROI is profit divided by staked units, with cancellation denominator policy specified in advance; zero exposure is undefined, not 0% success.
- Edge-band and weekly diagnostics: descriptive, using existing fixed bins where applicable (`<1%`, `1–2%`, `2–3%`, `3–4.25%` residual-movement bands are not offered-edge bands). Never select the best band or week range.
- Calibration: predeclared bins, mean probability and outcome frequency, tie handling and sample sizes.
- Drawdown: peak-to-trough cumulative flat-unit P&L under a predetermined chronological ordering; unavailable without reliable event/settlement ordering. No bankroll optimization.
- Qualifying-bet count and sample size: report initial population, joined, timing-proven, valid-feature, valid-market, rejected, no-bet, bet and settled counts.

None of these performance metrics was calculated or refreshed in Phase 4A. Prior reports' performance claims are historical records, not verified anew by this audit.

## Caesars and prospective separation

This audit provides **no reason to purchase Caesars access now**. Caesars-labelled historical prices are already present numerically; the missing facts are original timestamps, identities, source versions and rights. Prior Phase 2 records describe a paid entitlement that would enable a new Caesars conformance test; a purchase itself would not authenticate this workbook, repair spread pairs, establish historical EPA vintage, supply official kickoff revisions, or prove DraftKings state equivalence. Historical coverage would need separate evidence, not an inference from paid access. No current price or plan capability was re-verified in this offline audit.

Resolve historical feasibility before considering a purchase for historical research. Core-Three does not include Caesars; adding it would change the estimand. A future separately justified purchase decision must not be driven by selecting the best 2025 performance.

Historical research cannot populate a prospective ledger or count as prospective evidence. The original seven-book 2026 experiment remains CLOSED and unchanged. Core-Three remains separate, unfrozen and inactive; all Phase 3 external/provider/governance gates remain unresolved. Nothing here supplies an effective timestamp or authorizes collection.

## Validation and Git safety

- Relevant test run: **260 passed**, comprising recent-form feature/validation tests, historical-record/odds math tests, all eight frozen prospective suites and all five Core-Three suites. Synthetic week-exclusion perturbation checks: **4 passed**, separate from pytest.
- Stored-data checks: all 272 REG identity/date joins; 544 history-depth checks; null, duplicate, finite-value and feature-formula checks; workbook metadata/provenance scan; read-only database catalog inspection. Market/result failures are retained as findings, not repaired to make the audit pass.
- JSON parsing, in-memory compilation of all 286 Python files under `src` and `scripts`, credential scan, explicit new-file whitespace checks, `git diff --check` and `git diff --cached --check`: PASS. Compilation created no bytecode files.
- Ruff: unavailable; not installed. Runtime limitation: tests used Python 3.12.13 rather than declared 3.13.
- No existing tracked file changed. Historical files and ignored schedule/database/manifest hashes were checked for preservation. No new real manifest, ledger, raw capture, decision, or evidence was created.
- Ending SHA: `9ad202922ecb9da90df6470dbef4a0ff75e66a96`, unchanged and still equal to the named remote-tracking ref.
- Working tree after: only these two new, untracked/uncommitted Phase 4A reports. Existing files modified: none. Files staged: none. Commit: NO. Push: NO. PR: NO.

Created files:

1. `research/governance/step91o/step91o_phase4a_2025_data_leakage_audit.md`
2. `research/governance/step91o/step91o_phase4a_2025_data_leakage_audit.json`

## Safety report

Money spent: **$0**. Provider plan purchased: **NO**. Caesars activated: **NO**. Sports/provider API requests: **0** (package installation was not a sports-data request). Prospective evidence: **0**. Manifest and ledger: **untouched**. Candidate, coefficients, thresholds, residual cap, eligibility, consensus, execution venue and original seven-book protocol: **unchanged**. No 2026 outcomes evaluated. No optimization, recalibration or performance replay performed. **Activation remains prohibited. Stop after Phase 4A.**
