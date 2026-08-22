# ADR-034: Red-Zone Broad Search

## Status
Accepted for research.

## Context
67A produced leakage-safe red-zone artifacts for 2022-2025. 67B confirmed
roughly 94% feature coverage, stable distributions, and adequate historical
sample volume. 67C wired four independent red-zone signals into research.

66F previously promoted offensive sack-rate advantage at weight 10.0. That
signal is therefore part of the current v1.0 candidate baseline.

## Decision
67D measures the *marginal* value of red-zone features on top of the current
locked v1.0 passing signal rather than returning to an older weaker baseline.

The following red-zone families are tested independently.

### Offensive red-zone EPA/play
1, 2, 4, 6

### Defensive red-zone EPA allowed/play
1, 2, 4, 6

### Red-zone success-rate differential
5, 10, 15, 20

### Red-zone touchdown-play-rate differential
10, 20, 30, 40

The ranges are scale-aware relative to the distributions observed in 67B.

## Foundation
Every experiment retains:
- rest = 0.20
- offensive sack-rate advantage = 10.0
- QB = 0.00
- injury = 0.00
- early-down = 0.00
- turnover = 0.00
- all other passing weights = 0.00

## Baseline contract
`red_zone_v1_baseline` ends in `_baseline` so the existing research reporter can
resolve it without special handling.

## Interpretation
67D should identify which red-zone family, if any, adds value beyond the already
promoted passing signal. A feature that only beats the pre-66F model but does not
beat `red_zone_v1_baseline` does not earn promotion.

Do not promote directly from 67D. Fine-tune only families that show credible
marginal improvement.
