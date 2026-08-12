# ADR-015: Injury Availability Foundation

## Status
Accepted

## Verified schema difference
nflverse injury data for 2022-2024 contains `date_modified`.
The verified 2025 dataset contains 6,068 rows but does not expose
`date_modified`; it additionally exposes `season_type`.

A missing timestamp must not be interpreted as permission to use the
injury record historically.

## Severity mapping
Report severity:
- Out = 1.00
- Doubtful = 0.75
- Questionable = 0.40
- Note/null/unrecognized = 0.00

Practice severity:
- Did Not Participate In Practice = 0.50
- Limited Participation in Practice = 0.25
- Full Participation in Practice = 0.00
- Note/blank/null/unrecognized = 0.00

Player severity is the bounded maximum of report and practice severity.
Team scores are unweighted sums. No starter or player-value assumptions
are made.

## Leakage policy
`date_modified`, where present, is preserved as `source_modified_at`.
Its exact upstream semantics are not proven to be publication time.

Records without a source timestamp are retained in normalized data for
observability but are excluded from all injury scoring. Therefore the
verified 2025 source produces neutral/unknown injury features until a
trustworthy pregame timestamp becomes available.

When schedule data contains `kickoff_at`, timestamped records are eligible
only when `source_modified_at < kickoff_at`. Equal or later timestamps are
excluded.

## Production boundary
63A remains standalone. No production prediction, experiment, promotion,
rest-weight, or QB-weight behavior changes.
