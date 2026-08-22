# ADR-018: Injury Weight Fine-Tuning

## Status
Accepted for research.

## Context
Milestone 63C bracketed the aggregate injury-weight optimum around 0.90.
The aggregate leader was injury_090, while 1.50 was worse than baseline.

## Decision
63D tests:
- 0.00 baseline
- 0.70
- 0.75
- 0.80
- 0.85
- 0.90
- 0.95
- 1.00
- 1.05
- 1.10

Rest remains 0.20 and QB remains 0.00.

## Scope
Use only injury_modern: 2022, 2023, 2024.

## Production boundary
Research only. No production model setting changes.
