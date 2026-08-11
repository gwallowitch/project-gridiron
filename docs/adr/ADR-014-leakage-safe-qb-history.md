# ADR-014: Leakage-Safe Historical QB Intelligence

## Status
Accepted

## Decision
For game week W:
- starter proxy = team's primary passer from its most recent game before W;
- player efficiency = cumulative passing efficiency through W-1;
- league efficiency = cumulative league passing efficiency through W-1;
- Week 1 is neutral/unknown.

Efficiency:
`(passing_yards + 20 * passing_tds - 45 * interceptions) / attempts`

QB rating is the prior league-relative efficiency difference, shrunk toward zero
with 75 prior attempts, multiplied by 0.75, and clipped to [-6, +6].

## Leakage policy
Current-week and future-week performance are never used to rate the game being predicted.

## Limitation
The historical starter is a prior-game continuity proxy, not a perfect pregame
depth-chart reconstruction. Injury/announced-starter data can be added later.
