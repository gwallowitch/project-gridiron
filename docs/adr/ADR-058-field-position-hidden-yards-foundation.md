# ADR-058: Field Position / Hidden Yards Foundation

## Status
Accepted for research foundation.

## Context
Neutral-state, pressure, and third-down feature families failed to improve the
current candidate. Punt-return advantage did add value, suggesting that field
position and hidden yards may contain orthogonal information.

## Decision
74A introduces leakage-safe pregame field-position features derived from drive
starts.

A drive start is the first eligible run/pass snap for an offense within a drive.
`yardline_100` is used as distance from the opponent end zone; lower values
represent better offensive field position.

## Historical team features
Offense:
- drives started;
- average starting `yardline_100`;
- short-field rate (`yardline_100 <= 60`);
- long-field rate (`yardline_100 >= 80`).

Defense:
- opponent drives started;
- average opponent starting `yardline_100`;
- short-field rate allowed;
- long-field rate forced.

## Derived matchup features
- `off_start_field_position_advantage`
- `def_field_position_advantage`
- `short_field_rate_difference`
- `long_field_avoidance_advantage`
- `hidden_yards_field_position_advantage`

The hidden-yards composite is the sum of offensive and defensive starting-field
position advantages.

## Leakage policy
A week-N matchup uses only same-season drives from weeks strictly less than N.

## Scope
74A builds/persists features only. It does not modify model weights or
`config/experiments.toml`.

74B will validate historical coverage and sample depth before model wiring.
