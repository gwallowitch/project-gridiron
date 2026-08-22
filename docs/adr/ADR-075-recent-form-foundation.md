# ADR-075: Recent-Form Foundation

## Status
Accepted for research foundation.

## Context
Steps 75–77 rejected fourth-down, explosive-suppression, and turnover-stability
families as incremental additions to the current four-weight research lock.

The next feature family should capture information that season-to-date
efficiency metrics miss: teams that are materially improving or deteriorating.

## Decision
78A creates leakage-safe pregame recent-form features using the prior three
weeks, compared with the same team's season-to-date baseline through the prior
week.

Recent form is considered known when at least two prior weeks exist.

## Derived matchup features
- `recent_off_epa_difference`
- `recent_def_epa_advantage`
- `off_epa_trend_difference`
- `def_epa_trend_advantage`
- `off_success_trend_difference`
- `def_success_trend_advantage`

The two trend families compare recent performance with the team's own longer
season baseline, reducing overlap with static cumulative efficiency measures.

## Leakage rule
Only weeks strictly before the target game's week are eligible. Current-week
plays never enter the target game's features.

## Scope
78A builds and persists features only. It does not alter experiment weights,
runtime scoring, `config/experiments.toml`, or the current research lock.

78B will validate historical coverage, dispersion, and sample depth before any
experiment wiring.
