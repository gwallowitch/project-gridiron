# ADR-038: Drive Efficiency Foundation

## Status
Accepted for research foundation.

## Context
Project Gridiron has promoted offensive sack-rate advantage as a robust
incremental signal, while red-zone and rushing families did not add enough
marginal value. Milestone 69 moves to drive-level efficiency, a less redundant
feature family.

nflfastR recommends `fixed_drive` and `fixed_drive_result` over the raw NFL drive
field because the raw drive field can be inconsistent.

## Decision
69A introduces leakage-safe pregame drive-efficiency features:

Offense:
- EPA per drive;
- scoring-drive rate;
- touchdown-drive rate;
- plays per drive;
- prior drive volume.

Defense:
- EPA allowed per drive;
- scoring-drive rate allowed;
- touchdown-drive rate allowed;
- plays per drive allowed;
- prior drive volume faced.

Game-level derived features:
- `drive_off_epa_difference`
- `drive_def_epa_difference`
- `scoring_drive_rate_difference`
- `td_drive_rate_difference`
- `plays_per_drive_difference`

All derived differences are home-centered.

## Scoring-drive definition
A scoring drive is a drive whose `fixed_drive_result` is `Touchdown` or
`Field goal`.

## Points per drive
69A intentionally does not create a synthetic points-per-drive metric by mapping
drive results to assumed point values. EPA/drive and scoring/TD drive rates are
used instead so the first implementation stays directly grounded in nflverse
fields.

## Three-and-out rate
Three-and-out rate is deferred from 69A. It requires a more explicit decision
about qualifying offensive plays and punt bookkeeping. We will add it only if
drive efficiency proves useful enough to justify a second drive-engineering pass.

## Leakage rule
For a game in week N, only same-season drives from weeks strictly less than N
may contribute.

## Scope
69A creates and validates artifacts only. It does not modify experiment weights
or production prediction behavior.
