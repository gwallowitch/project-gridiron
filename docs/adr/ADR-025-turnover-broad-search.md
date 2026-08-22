# ADR-025: Turnover Broad Weight Search

## Status
Accepted for research.

## Context
65A/65B produced leakage-safe historical turnover artifacts for 2022-2025.
Interceptions and lost fumbles are stored separately, and 65C wired them as
independent experiment inputs.

## Decision
65D tests the two turnover components independently.

### Interception weights
- 0.50
- 1.00
- 1.50
- 2.00
- 3.00

### Lost-fumble weights
- 0.25
- 0.50
- 0.75
- 1.00
- 1.50

A zero-weight baseline is retained.

## Foundation
This is an isolated turnover study:
- rest = 0.20
- QB = 0.00
- injury = 0.00
- early-down offense = 0.00
- early-down defense = 0.00
- early-down success = 0.00

The goal is to identify whether interceptions, lost fumbles, both, or neither
carry useful marginal predictive value before combined-feature testing.

## Season scope
Use the modern profile: 2022-2025.

Week 1 remains in the backtest with turnover adjustments neutral-filled to zero.

## Interpretation
65D should answer:
1. Does interception history improve the model?
2. Does lost-fumble history improve the model?
3. Is the best candidate interior or on a grid boundary?
4. Is either signal inconsistent enough to reject immediately?

Do not promote from 65D. Fine-tune only the signal families that earn it.
