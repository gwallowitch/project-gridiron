# ADR-093 — Travel Fatigue Rejection Lock

## Status
Accepted.

## Decision
Step 81C rejected ordinary travel burden as a model-weight family.

Across 2022–2025, the existing six-weight baseline ranked first. The strongest
travel candidate, `travel_tz_010`, had a +0.0003 mean score delta, -0.4% mean
accuracy delta, a 2-2 season record, and a 95% confidence interval of
[-0.0001, 0.0011]. Positive score delta is worse.

The distance family was also unfavorable; `travel_miles_010` produced a
+0.0005 mean score delta and -0.4% mean accuracy delta.

## Lock
Step 81D preserves the promoted six-weight model:

- rest = 0.20
- offensive sack = 10.00
- punt return = 0.24
- long-field avoidance = 1.00
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25

Travel fields remain available for future research, but active weights are
locked to zero:

- travel miles = 0.0
- travel time zone = 0.0

Short-week travel interactions remain unpromoted.

## Next
Step 82 should move to a new orthogonal feature family rather than fine-tune a
travel signal that failed the broad screen.
