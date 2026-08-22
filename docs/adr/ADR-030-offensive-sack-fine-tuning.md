# ADR-030: Offensive Sack-Rate Fine-Tuning

## Status
Accepted for research.

## Context
66D tested six passing feature families independently.

Offensive sack-rate advantage was the strongest family:
- weight 10 went 4-0 across seasons and had a confidence interval entirely
  favorable to the candidate;
- weight 20 had the best aggregate score and the largest observed accuracy
  improvement among the broad passing candidates;
- higher weights remained competitive but became less stable.

The other passing families either showed weaker, inconsistent, or harmful
results and are not fine-tuned in 66E.

## Decision
66E fine-tunes offensive sack-rate advantage at:

0, 5, 8, 10, 12, 15, 18, 20, 22, 25

All other passing weights remain zero.

## Foundation
The isolated research foundation remains:
- rest = 0.20
- QB = 0.00
- injury = 0.00
- early-down = 0.00
- turnover = 0.00
- all other passing families = 0.00

## Season scope
Use the modern profile: 2022-2025.

## Interpretation
66E should determine whether the robust 10-weight result or the stronger
aggregate 20-weight result survives a denser local search.

66F will make the keep/reject or promotion decision. No production setting is
changed by 66E.
