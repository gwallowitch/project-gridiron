# ADR-023: Turnover Regression Foundation

## Status
Accepted for research foundation.

## Decision
Milestone 65A introduces a standalone, leakage-safe turnover feature family.

Interceptions and lost fumbles remain separate. We do not assume they have the
same persistence or predictive value. The initial artifact records:
- interceptions thrown per prior game;
- lost fumbles per prior game;
- total turnovers committed per prior game;
- home-away differences;
- prior-history coverage flags.

Only games from the same season with `week < prediction week` are eligible.

## Important limitation
65A is a foundation, not the regression model itself. It deliberately does not
assign predictive weights, regress fumbles toward a league mean, wire features
into predictions, or promote anything to production.

Those decisions belong to later 65 milestones after historical artifacts are
validated.

## Leakage policy
No current-game or future-week play-by-play may contribute to a game's
pregame turnover features.

## v1.0 policy
Production turnover weights remain zero until multi-season research supports
promotion.
