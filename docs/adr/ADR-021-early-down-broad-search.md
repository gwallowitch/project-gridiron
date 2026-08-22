# ADR-021: Early-Down Broad Weight Search

64D tests early-down offense, defense, and success rate independently.

- Offensive EPA weights: 2, 4, 6, 8, 10
- Defensive EPA weights: 2, 4, 6, 8, 10
- Success-rate weights: 5, 10, 15, 20

Foundation is rest=0.20, QB=0.00, injury=0.00. Injury is neutral here so we can
measure standalone early-down value before later combined-feature interaction
testing.

Use the modern profile: 2022-2025. Week 1 is neutral-filled by 64C.

Do not promote from 64D; fine-tune promising signals in 64E.
