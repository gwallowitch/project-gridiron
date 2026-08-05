# ADR-006: Rest Differential Features

## Status

Accepted

## Context

Project Gridiron needs new predictive inputs that can be calculated
deterministically from historical schedules without relying on external
injury or market data.

## Decision

Create a first-class `rest_features` dataset with one row per game:

- `home_rest_days`
- `away_rest_days`
- `rest_advantage`

Rest is measured as calendar days since each team's previous game.
A team's first game of the season receives a neutral seven-day default.

## Consequences

- The feature is reproducible from schedule data alone.
- Bye weeks and short weeks emerge naturally from game dates.
- Production predictions remain unchanged until an experiment proves a
  useful rest coefficient.
- Postseason rest is calculated continuously within the same season.
