# ADR-050: Pressure and Pass-Protection Foundation

## Status
Accepted for research foundation.

## Context
The passing research found offensive sack rate useful, while third-down efficiency
did not add meaningful incremental signal. Step 72 begins a distinct but related
family: the ability to prevent and create quarterback pressure before it becomes
a sack.

## Data contract
The initial implementation deliberately uses only nflverse play-by-play fields
already available to Project Gridiron:

- `qb_hit`
- `sack`
- pass play identity
- EPA

A pressure event is conservatively defined as `qb_hit OR sack`. This is a
**pressure proxy**, not a claim that complete hurry/pressure tracking is
available. No proprietary charting data is required.

## Pregame features
The artifact contains historical, same-season, strictly-prior-week measures for:

- offensive pressure allowed rate
- offensive clean-dropback rate
- offensive EPA on pressured plays
- defensive pressure creation rate
- defensive EPA allowed on pressured plays
- supporting event/dropback counts

Home-centered matchup differences are emitted for research.

## Leakage policy
For a game in week N, only observations from weeks `< N` are eligible.
Current-week outcomes are never used.

## Research plan
72A builds the feature foundation only.
72B will validate historical coverage/distributions.
72C will wire candidate weights.
72D will perform broad independent research against the current locked candidate.
