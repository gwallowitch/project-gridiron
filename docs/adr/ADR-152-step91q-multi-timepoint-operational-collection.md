# ADR-152: Step 91Q Multi-Timepoint Operational Collection

## Status

Accepted for bounded implementation as non-prospective operational collection.

## Decision

Step 91Q provides a deterministic command suitable for periodic invocation by
Windows Task Scheduler. It reads the retained 2026 REG Week 1–16 schedule from
`data/raw/schedules/step91i_schedules_2026_reg_weeks_01_16.json`; it does not run
a daemon or fetch schedule data. Kickoff revision handling remains a documented
limitation because this retained schedule has no revision-history mechanism.

The fixed collection policy is:

| Label | Target | Inclusive tolerance |
|---|---:|---:|
| `T12H` | 720 minutes | 660–780 minutes |
| `T6H` | 360 minutes | 330–390 minutes |
| `T3H` | 180 minutes | 150–210 minutes |
| `T1H` | 60 minutes | 45–75 minutes |
| `NEAR_KICKOFF` | 15 minutes | 5–30 minutes |

Actual collection timestamp, minutes and hours to kickoff remain authoritative;
labels never replace actual timing. Windows are frozen observational policy and
must not be optimized using 2026 outcomes or early profitability.

Collection-target metadata uses a separate canonical, append-only log at
`data/operational/collection_attempts_v1.jsonl`. This avoids changing the
immutable Step 91P schema-v2 observation. Each attempt records target and actual
timing, bounded result/reason codes, a content identity, and the linked Step 91P
observation identity on success. The reader validates content identities,
derived timing, bounded semantics, and uniqueness of `game_id + target`.

Before spending an API credit, the collector validates both retained logs,
checks local schedule eligibility and prior attempts, and obtains the existing
automatic DEF EPA value. An eligible target uses exactly one existing
`fetch_live_prices()` call, then the existing game-day snapshot and operational
prediction, and finally the existing Step 91P append. Persistence never refetches.
One game failure does not stop another eligible game.

Every automated Step 91Q observation records an exact target marker in the
existing Step 91P `provider` provenance field. Manual game-day observations keep
their existing provider identities and therefore cannot be confused with an
automatic target solely because game identity or timing happens to match.

Cross-file persistence is recoverable rather than destructive. Step 91P is
appended first and is never rolled back, truncated, or rewritten if the linked
attempt-log append fails. That bounded failure is reported as
`ATTEMPT_LOG_APPEND_FAILED`. On the next invocation, the collector recognizes
the exact automatic `(game_id, target marker)` observation, verifies that its
actual timing is inside the marked window, and appends a `SUCCESS` attempt using
the original observation identity and timestamp with reason
`RECOVERED_SUCCESS`. It performs no provider request and creates no second Step
91P row during reconciliation. Duplicate or contradictory automatic markers
fail closed.

The complete retained history and attempt log are validated globally at startup;
corruption there aborts collection. A bounded attempt-log persistence failure
during one game triggers an immediate read-only revalidation of the log. If the
log remains trustworthy, that game is reported failed and later games continue;
if revalidation detects corruption, collection fails globally.

A prior attempt makes its game/target ineligible for another automatic request;
a successful attempt is reported as already complete. A passed target becomes
`MISSED_WINDOW` and is never relabeled, backdated, or filled with historical
odds. A later currently eligible target may still run. Games already completed
before execution are reported but no retrospective attempt or observation is
written, preventing historical backfill. Manual game-day history capture remains
unchanged and independent.

`--dry-run` performs no provider calls and no writes. It reports eligible,
completed, missed, and post-kickoff classifications from local state only.

This facility is explicitly non-prospective. It does not calculate CLV, inspect
outcomes, tune a model, alter the frozen directional decision or two-sided
challenger, or write the Step 91B manifest, ledger, evidence, or formal capture
records. The frozen decision remains the only sportsbook recommendation.
