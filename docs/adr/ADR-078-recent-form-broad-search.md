# ADR-078: Recent-Form Broad Search

## Status
Accepted for controlled research.

## Baseline
78D evaluates six recent-form/trend signals on top of the current four-weight
research lock:

- rest = 0.20
- offensive sack = 10.0
- punt return = 0.24
- long-field avoidance = 1.00

Rejected fourth-down, explosive-suppression, and turnover-stability families
remain parked at zero.

## Grid
One baseline plus 24 single-variable candidates:

- recent offense EPA: 0.5, 1.0, 2.0, 4.0
- recent defense EPA: 0.5, 1.0, 2.0, 4.0
- offense EPA trend: 0.5, 1.0, 2.0, 4.0
- defense EPA trend: 0.5, 1.0, 2.0, 4.0
- offense success trend: 5, 10, 15, 20
- defense success trend: 5, 10, 15, 20

Only one recent-form research weight is active per candidate.

## Promotion rule
78D is a screening step. 78E fine tuning is warranted only if a recent-form
candidate improves the cross-season selection score versus the approximately
0.4668 locked benchmark without unacceptable winner-accuracy degradation.
