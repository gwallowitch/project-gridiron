# ADR-154: Step 91S totals activation and Week 2 readiness

## Status

Accepted for activation preparation and read-only readiness auditing. This change does not register a scheduled task or activate collection.

## Decision

Step 91R remains a separate, non-prospective three-book totals observation lane. Step 91S adds deterministic Windows Task Scheduler instructions and a read-only health check for its separate history and attempt logs. The totals collector remains independent of the live moneyline collector. No totals prediction, recommendation, model, backfill, outcome analysis, or historical optimization is introduced.

The health check validates both append-only files and cross-file SUCCESS linkage without requests, writes, recovery, or repair. Missing files are a valid empty state. Corruption fails closed; an automatic observation without its SUCCESS attempt is reported as requiring the existing Step 91R recovery path.

Week 2 is the first week where the frozen DEF EPA path must successfully consume real 2026 prior-week data. It is not the first potentially non-zero trend week. With only Week 1 eligible, each team’s season and recent defensive EPA aggregates are identical. Each improvement and their home-minus-away advantage are therefore necessarily a legitimately computed `0.0`. This provenance is distinct from the explicit Week 1 neutral fallback.

The audit clears the current-season nflverse cache before loading, selects only 2026 Week 1 play-by-play, invokes the unchanged frozen feature builder, requires both teams’ defensive inputs, and verifies the computed-zero invariant. Missing inputs fail closed. No prior season, current Week 2, future week, carryover, alternate baseline, changed window, recalibration, or frozen model change is permitted. The coefficient remains `+1.044827`.
