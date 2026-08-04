# ADR-002: Prior-Week Strength of Schedule

## Status

Accepted

## Context

Project Gridiron requires a transparent and backtestable measure of opponent
quality before opponent-adjusted power ratings can be calculated. Using final
season ratings or same-week ratings would introduce future information into
historical analyses.

## Decision

For each team in week `N`:

1. Collect every opponent faced through week `N`.
2. Value each opponent using its overall team rating from week `N - 1`.
3. Use a neutral rating of `100.0` when no prior-week rating exists.
4. Average those opponent ratings to produce the team's weekly strength of
   schedule rating.

Week 1 is always assigned the neutral baseline of `100.0` because no prior-week
ratings exist.

## Consequences

- Historical calculations remain free of future leakage.
- The method is deterministic and directly explainable.
- Early-season values are less stable and may contain neutral fallbacks.
- Repeated opponents are counted once per game, matching the schedule actually
  played.
- Future versions may add offense-specific, defense-specific, or recency-
  weighted schedule measures without changing this baseline definition.
