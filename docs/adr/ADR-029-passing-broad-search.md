# ADR-029: Passing Efficiency Broad Search

## Status
Accepted for research.

## Context
66A produced leakage-safe passing artifacts for 2022-2025. 66B confirmed
stable distributions and ~94.4% coverage, with the expected Week 1 history gap.
66C wired six independent passing signals into the research engine.

## Decision
66D tests each passing family independently before any combination search.

### Offensive EPA / dropback
1, 2, 4, 6

### Defensive EPA allowed / dropback
1, 2, 4, 6

### Passing success-rate differential
5, 10, 15, 20

### Offensive sack-rate advantage
10, 20, 30, 40

### Defensive sack-rate advantage
10, 20, 30, 40

### Explosive-pass-rate differential
10, 20, 30, 40

The ranges are deliberately scale-aware. EPA differences historically have
larger dispersion than success-rate differences, while sack/explosive-rate
differences are smaller still.

## Foundation
The isolated research baseline is:
- rest = 0.20
- QB = 0.00
- injury = 0.00
- early-down weights = 0.00
- turnover weights = 0.00

This avoids attributing interaction effects to the passing family before its
standalone value is understood.

## Season scope
Use the modern profile: 2022-2025.

## Interpretation
66D should identify:
1. which passing families are helpful,
2. which are harmful or redundant,
3. whether the best candidate is at a search boundary,
4. which families deserve 66E fine-tuning.

Do not promote directly from 66D.
