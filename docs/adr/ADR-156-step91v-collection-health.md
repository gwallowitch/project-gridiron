# ADR-156: Step 91V collection health and coverage audit

## Status

Accepted for implementation as a read-only, non-prospective observability layer.

## Decision

Step 91V audits the canonical retained schedule, Step 91P/91R observation
histories, and Step 91Q/91R attempt logs without fetching odds or writing any
state. It reuses the collectors' authoritative frozen windows and asserts that
moneyline and totals definitions are identical at import time.

Each lane and target is classified as `NOT_YET_DUE`, `IN_WINDOW_PENDING`,
`SUCCESS`, `FAILED_IN_WINDOW`, `MISSED_WINDOW`,
`WINDOW_EXPIRED_NO_SUCCESS`, `POST_KICKOFF_NO_SUCCESS`,
`RECOVERY_REQUIRED`, or `INVALID_EVIDENCE`. A persisted automatic observation
is successful only when actual timing is inside the frozen window and its
SUCCESS attempt links the same observation, kickoff, and timestamp. An orphan
observation exposes the existing collector recovery condition; the audit does
not perform recovery. Malformed logs fail closed.

Provider failure and absence are different facts. A retained failed attempt is
`FAILED_IN_WINDOW` with its provider/validation reason. No attempt after an
expired window is `WINDOW_EXPIRED_NO_SUCCESS` with `NO_ATTEMPT_OBSERVED`; this
does not claim Windows Task Scheduler failed because no scheduler event log is
consumed.

Lane summaries are `NOT_YET_ACTIVE`, `HEALTHY`, `ACTION_NEEDED`, `DEGRADED`,
`INVALID`, or `GAME_COMPLETE`. Future windows are not missing. A currently open
window without success is actionable. `--as-of` makes reconstruction
deterministic; `--game` audits one exact canonical identity, while the bounded
upcoming scan defaults to actionable games and `--all` includes healthy games.
Exit 0 means no displayed action is required, 1 means action/degradation is
present, and 2 means evidence or input is invalid.

The DEN-KC missed and failed windows remain motivating operational evidence,
not a backfill request. Step 91V cannot retry, repair, create observations,
predict, recommend, execute, settle, or prove scheduler failure. It changes no
model, protocol, DEF EPA, book, window, execution, prospective-evidence, or
Step 91U final-result authority semantics.
